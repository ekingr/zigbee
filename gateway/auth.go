package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/url"
)

type authApi struct {
	app        string
	url        string
	key        string
	CookieName string
}

type authorization struct {
	User string `json:"user"`
}

func (auth *authApi) Authorize(sid, lvl string) (bool, *authorization, error) {
	params := url.Values{
		"app": {auth.app},
		"key": {auth.key},
		"sid": {sid},
		"lvl": {lvl},
	}
	r, err := http.Get(auth.url + "?" + params.Encode())
	if err != nil {
		return false, nil, err
	}
	if r.StatusCode == http.StatusForbidden {
		return false, nil, nil
	}
	if r.StatusCode == http.StatusOK {
		var a authorization
		err := json.NewDecoder(r.Body).Decode(&a)
		return true, &a, err
	}
	return false, nil, errors.New(fmt.Sprintf("Unknown response form auth backend: %d", r.StatusCode))
}

// Authentication check middleware
func (s *server) authCheck(level string, h http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// Getting session id
		cookie, err := r.Cookie(s.auth.CookieName)
		if err != nil {
			s.logger.Println("Error getting SID from cookie:", err)
			http.Error(w, "Forbidden", http.StatusForbidden)
			return
		}
		sid, err := url.QueryUnescape(cookie.Value)
		if err != nil {
			s.logger.Println("Error getting SID from cookie:", err)
			http.Error(w, "Forbidden", http.StatusForbidden)
			return
		}

		// Authorizing
		ok, auth, err := s.auth.Authorize(sid, level)
		if err != nil {
			s.logger.Println("Error authenticating:", err)
			http.Error(w, "Forbidden", http.StatusForbidden)
			return
		}
		if !ok {
			s.logger.Println("Unauthorized")
			http.Error(w, "Forbidden", http.StatusForbidden)
			return
		}

		// Passing user value forward
		r.Header.Set("x-internal_-user", auth.User)
		h(w, r)
	}
}
