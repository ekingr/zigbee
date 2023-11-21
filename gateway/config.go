package main

import (
	"encoding/json"
	"os"
	"sync"
)

type config struct {
	Devices []device `json:"devices"`
	Rules   []rule   `json:"rules"`
}

type configStore interface {
	GetDevices() []device
	GetRules() []rule
	SetDevices(devices []device) error
	SetRules(rules []rule) error
}

// Implementation of configStore using a JSON file on disk.
// Config is read from disk at creation then kept in memory for later access (GetX methods).
// Config is writtent on disk after each change (SetX methods).
type configStoreJson struct {
	fileName string       // Path to the JSON file
	mmu      sync.RWMutex // Mutex for syncing access to the memory config
	fmu      sync.RWMutex // Mutex for syncinc access to the config file on disk
	cfg      config       // Cached version of the config
}

func newConfigStoreJson(fileName string) (*configStoreJson, error) {
	st := &configStoreJson{fileName: fileName}
	// Checking ability to read & write
	err := st.readConfig()
	if err != nil {
		return nil, err
	}
	err = st.writeConfig()
	if err != nil {
		return nil, err
	}
	return st, nil
}

func (st *configStoreJson) readConfig() error {
	st.fmu.RLock()
	defer st.fmu.RUnlock()
	fd, err := os.Open(st.fileName)
	if err != nil {
		return err
	}
	defer fd.Close()
	st.mmu.Lock()
	defer st.mmu.Unlock()
	err = json.NewDecoder(fd).Decode(&st.cfg)
	return err
}

func (st *configStoreJson) writeConfig() error {
	st.fmu.Lock()
	defer st.fmu.Unlock()
	fd, err := os.Create(st.fileName)
	if err != nil {
		return err
	}
	defer fd.Close()
	st.mmu.RLock()
	defer st.mmu.RUnlock()
	enc := json.NewEncoder(fd)
	enc.SetIndent("", "\t")
	return enc.Encode(&st.cfg)
}

func (st *configStoreJson) GetDevices() []device {
	st.mmu.RLock()
	defer st.mmu.RUnlock()
	return st.cfg.Devices
}

func (st *configStoreJson) GetRules() []rule {
	st.mmu.RLock()
	defer st.mmu.RUnlock()
	return st.cfg.Rules
}

func (st *configStoreJson) SetDevices(devices []device) error {
	func() {
		// Need to release mmu lock before calling writeConfig
		st.mmu.Lock()
		defer st.mmu.Unlock()
		st.cfg.Devices = devices
	}()
	return st.writeConfig()
}

func (st *configStoreJson) SetRules(rules []rule) error {
	func() {
		// Need to release mmu lock before calling writeConfig
		st.mmu.Lock()
		defer st.mmu.Unlock()
		st.cfg.Rules = rules
	}()
	return st.writeConfig()
}
