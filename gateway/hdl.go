package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

// get status (GET)
func (s *server) getStatus() http.HandlerFunc {

	type response struct {
		apiState
		Rules   []rule   `json:"rules"`
		Devices []device `json:"devices"`
	}
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-type", "application/json; charset=UTF-8")
		err := json.NewEncoder(w).Encode(&response{
			apiState: s.gateway.GetState(),
			Rules:    s.ruler.GetRules(),
			Devices:  s.config.GetDevices(),
		})
		if err != nil {
			s.logger.Println("Error marshalling response status to JSON:", err)
			http.Error(w, "Internal Server Error", http.StatusInternalServerError)
			return
		}
	}
}

// set status (POST)
func (s *server) postSetState() http.HandlerFunc {
	type request struct {
		State zbState `json:"state"`
	}
	return func(w http.ResponseWriter, r *http.Request) {
		// Parsing and checking JSON request
		var req request
		err := json.NewDecoder(r.Body).Decode(&req)
		if err != nil {
			s.logger.Println("Error parsing input: ", err)
			http.Error(w, "Bad Request", http.StatusBadRequest)
			return
		}

		// Setting devices state
		if err := s.gateway.SetState(req.State); err != nil {
			s.logger.Println("Error setting state to", req.State, ":", err)
			http.Error(w, "Internal Server Error", http.StatusInternalServerError)
			return
		}

		// Writing response
		s.logger.Println("State set to", req.State)
		fmt.Fprint(w, "OK")
	}
}

// set rules (POST)
func (s *server) postSetRules() http.HandlerFunc {
	type request struct {
		Rules []rule `json:"rules"`
	}
	return func(w http.ResponseWriter, r *http.Request) {
		// Parsing and checking JSON request
		var req request
		err := json.NewDecoder(r.Body).Decode(&req)
		if err != nil {
			s.logger.Println("Error parsing input: ", err)
			http.Error(w, "Bad Request: malformed input", http.StatusBadRequest)
			return
		}
		knownDevices := s.gateway.GetState().Zigbee
		for i, r := range req.Rules {
			if r.Repeat != 0 && r.Repeat < rulerMinRepeatPeriod {
				s.logger.Println("Invalid input: repeat period too low")
				http.Error(w, "Bad Request: repeat period too low", http.StatusBadRequest)
				return
			}
			for device, newState := range r.NewState {
				if newState != 1 && newState != 0 {
					s.logger.Println("Invalid input: target new state should be 0 or 1")
					http.Error(w, "Bad Request: invalid target new state", http.StatusBadRequest)
					return
				}
				if _, ok := knownDevices[device]; !ok {
					s.logger.Println("Invalid input: target device not known")
					http.Error(w, "Bad Request: unknown target device", http.StatusBadRequest)
					return
				}
			}
			if r.Timestamp.Location() != time.UTC {
				req.Rules[i].Timestamp = r.Timestamp.UTC()
			}
		}

		// Setting rules
		s.ruler.SetRules(req.Rules)

		// Writing response
		s.logger.Println("Rules set to", req.Rules)
		fmt.Fprint(w, "OK")
	}
}
