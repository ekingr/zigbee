package main

import (
	"log"
	"sync"
	"time"
)

type rule struct {
	Name      string        `json:"name"`
	NewState  zbState       `json:"newState"`
	Timestamp time.Time     `json:"timestamp"`
	Repeat    time.Duration `json:"repeat"`
	Enabled   bool          `json:"enabled"`
}

func (r *rule) Copy() rule {
	return rule{
		Name:      r.Name,
		NewState:  r.NewState.Copy(),
		Timestamp: r.Timestamp,
		Repeat:    r.Repeat,
		Enabled:   r.Enabled,
	}
}

type ruler struct {
	gateway *gateway
	cfg     configStore
	log     *log.Logger
	mu      sync.Mutex
	rules   []rule
	quit    chan bool
}

// Ruler will check rules for execution every `rulerPeriod` (frequency of execution)
const rulerPeriod = 1 * time.Minute

// Rules older than `rulerOldestAge` will not be executed (only repeated if relevant)
const rulerOldestAge = 6 * time.Hour

// Rules cannot have a `Repeat` period lower than `rulerMinRepeatPeriod`, to avoid sending requests at too high a frequency
const rulerMinRepeatPeriod = 10 * time.Minute

func newRuler(g *gateway, cfg configStore, log *log.Logger) (r *ruler, err error) {
	r = &ruler{
		gateway: g,
		cfg:     cfg,
		log:     log,
		quit:    make(chan bool),
		rules:   cfg.GetRules(),
	}
	ticker := time.NewTicker(rulerPeriod)
	go func() {
		for {
			select {
			case now := <-ticker.C:
				go r.rule(now)
			case <-r.quit:
				ticker.Stop()
				return
			}
		}
	}()
	return
}

func (r *ruler) Close() {
	close(r.quit)
}

func (rlr *ruler) rule(now time.Time) {
	rlr.mu.Lock()
	defer rlr.mu.Unlock()
	change := false
	rlr.log.Println("Ruler: checking for rules to run...")
	rlr.log.Println("Ruler: current rules:", rlr.rules)
	//var expiredRuleIds []int
	for i := range rlr.rules {
		r := &rlr.rules[i] // getting a pointer to modify object directly
		if r.Enabled && (r.Timestamp.Before(now) || r.Timestamp.Equal(now)) {
			if r.Timestamp.Add(rulerOldestAge).Before(now) {
				rlr.log.Println("Ruler: rule too old, skipping:", r)
			} else {
				rlr.log.Println("Ruler: running rule:", r)
				// running SetState with a *deep* copy to avoid concurrency issues (range only performs a shallow copy, not sufficient for newState)
				go rlr.gateway.SetState(r.NewState.Copy())
			}
			change = true
			if r.Repeat > 0 {
				for r.Timestamp.Before(now) || r.Timestamp.Equal(now) {
					r.Timestamp = r.Timestamp.Add(r.Repeat)
				}
				rlr.log.Println("Ruler: repeating rule, updating target timestamp:", r)
			} else {
				r.Enabled = false
				rlr.log.Println("Ruler: disabling rule:", r)
				//expiredRuleIds = append(expiredRuleIds, i)
			}
		}
	}
	if change {
		rlr.cfg.SetRules(rlr.rules)
	}
	/* Keep expired rules for now (as disabled)
	// Update rules: keep only the ones that are not expired
	// expiredRuleIds is *ordered*
	updatedRules := make([]rule, len(rlr.rules)-len(expiredRuleIds))
	i0 := 0
	di := 0
	for _, dd := range append(expiredRuleIds, len(rlr.rules)) {
		for i := i0; i < dd; i++ {
			updatedRules[i-di] = rlr.rules[i]
		}
		i0 = dd + 1
		di++
	}
	rlr.rules = updatedRules
	*/
}

func (rlr *ruler) GetRules() []rule {
	rlr.mu.Lock()
	defer rlr.mu.Unlock()
	if rlr.rules == nil {
		return nil
	}
	// Return a deep copy to avoid concurrency issues
	rules := make([]rule, len(rlr.rules))
	for i, r := range rlr.rules {
		rules[i] = r.Copy()
	}
	return rules
}

func (rlr *ruler) SetRules(rules []rule) {
	rlr.mu.Lock()
	defer rlr.mu.Unlock()
	// Should not need to make a deep copy, as rules are not touched by the caller afterwards
	rlr.rules = rules
	rlr.cfg.SetRules(rules)
}
