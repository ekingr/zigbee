package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

type server struct {
	domain  string
	apiRoot string
	srv     *http.Server
	router  *http.ServeMux
	logger  *log.Logger
	auth    *authApi
	gateway *gateway
	ruler   *ruler
	config  configStore
}

func main() {
	s := server{
		domain:  "zigbee.my.example.com",
		apiRoot: "/api/zigbee/",
	}
	var err error

	// Logger
	s.logger = log.New(os.Stdout, "zigbee: ", log.LstdFlags)

	// Config
	prefix := "ZBGATEWAY"
	cfgFileName, ok := os.LookupEnv(prefix + "CONFIG")
	if !ok {
		s.logger.Fatal("Error: missing " + prefix + "CFG env config eg. /home/xxx/apps/www/zbGateway/config.json")
	}
	srvListen, ok := os.LookupEnv(prefix + "ADDR")
	if !ok {
        s.logger.Fatal("Error: missing " + prefix + "ADDR env config eg. 127.0.xxx.xxx:yyy")
	}
	authApiUrl, ok := os.LookupEnv(prefix + "AUTHAPIURL")
	if !ok {
		s.logger.Fatal("Error: missing " + prefix + "AUTHAPIURL env config")
	}
	authApiKey, ok := os.LookupEnv(prefix + "AUTHAPIKEY")
	if !ok {
		s.logger.Fatal("Error: missing " + prefix + "AUTHAPIKEY env config (base64-encoded)")
	}
	authCookieName, ok := os.LookupEnv(prefix + "AUTHCOOKIE")
	if !ok {
		s.logger.Fatal("Error: missing " + prefix + "AUTHCOOKIE env config")
	}
	zbRPCAddr, ok := os.LookupEnv(prefix + "RPCADDR")
	if !ok {
		s.logger.Fatal("Error: missing " + prefix + "RPCADDR env config -- zbCtrl gRPC address")
	}
	zbRPCCert, ok := os.LookupEnv(prefix + "RPCCERT")
	if !ok {
		s.logger.Fatal("Error: missing " + prefix + "RPCCERT env config -- zbCtrl gRPC ssl certificate")
	}
	zbRPCKey, ok := os.LookupEnv(prefix + "RPCKEY")
	if !ok {
		s.logger.Fatal("Error: missing " + prefix + "RPCKEY env config -- zbCtrl gRPC API key")
	}

	// Config file
	s.config, err = newConfigStoreJson(cfgFileName)
	if err != nil {
		s.logger.Fatal("Error loading config file:", err.Error())
	}
	s.logger.Println("Config: Loaded rules:", s.config.GetRules())
	s.logger.Println("Config: Loaded devices:", s.config.GetDevices())
	// No need to save before closing, as current config is written to disk after each change

	// Auth API
	s.auth = &authApi{
		app:        "zigbee",
		url:        authApiUrl,
		key:        authApiKey,
		CookieName: authCookieName,
	}

	// Gateway
	s.gateway, err = newGetway(zbRPCAddr, zbRPCKey, zbRPCCert, s.logger)
	if err != nil {
		s.logger.Fatal("Error setting-up the gateway:", err.Error())
	}
	defer s.gateway.Close()

	// Ruler
	s.ruler, err = newRuler(s.gateway, s.config, s.logger)
	if err != nil {
		s.logger.Fatal("Error setting-up the ruler:", err.Error())
	}
	defer s.ruler.Close()

	// Router
	s.router = http.NewServeMux()
	s.routes()

	// Server
	s.srv = &http.Server{
		Addr:         srvListen,
		Handler:      s.logMid(s.router),
		ErrorLog:     s.logger,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 10 * time.Second,
		IdleTimeout:  15 * time.Second,
	}

	// Handling graceful shutdown & starting server
	srvClosed := make(chan struct{})
	go func() {
		sigint := make(chan os.Signal, 1)
		signal.Notify(sigint, syscall.SIGINT, syscall.SIGTERM)
		<-sigint
		s.logger.Println("Received interrupt, shutting down server...")
		if err := s.srv.Shutdown(context.Background()); err != nil {
			s.logger.Fatal("Error shutting down server:", err)
		}
		close(srvClosed)
	}()
	s.logger.Println("Starting server:", s.srv)
	if err := s.srv.ListenAndServe(); err != http.ErrServerClosed {
		s.logger.Fatal("Server error:", err)
	}

	<-srvClosed
	s.logger.Println("Server closed. Bye!")
}
