package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"sync"
	"time"

	"google.golang.org/grpc"
	grpcCredentials "google.golang.org/grpc/credentials"
	grpcStatus "google.golang.org/grpc/status"

	pb "git.ekin.gr/zbGateway/proto"
)

// Frequency of state update from zbCtrl
const updatePeriod = 1 * time.Second

// Timeout for getState gPRC requests ot zbCtrl
const zbRPCTimeoutGet = 1 * time.Second

// Timeout for setState gPRC requests ot zbCtrl
const zbRPCTimeoutSet = 5 * time.Second

type dId string
type dState int

type device struct {
	Id   dId    `json:"id"`
	Name string `json:"name"`
	Type string `json:"type"`
}
type zbState map[dId]dState

func (s *zbState) Copy() zbState {
	newState := make(zbState)
	for d, ds := range *s {
		newState[d] = ds
	}
	return newState
}

type gateway struct {
	state        zbState
	updateOk     bool
	updateStatus string
	updateTime   int64
	zbRPCConn    *grpc.ClientConn
	zbRPCKey     string
	zbCtrl       pb.ZBCtrlClient
	running      bool
	mu           sync.RWMutex
}

type ZbRCPError struct {
	Status string
}

func (e *ZbRCPError) Error() string {
	return "Error from zbCtrl gRPC: " + e.Status
}

func newGetway(zbRPCAddr, zbRPCKey, zbRPCCert string, log *log.Logger) (g *gateway, err error) {
	creds, err := grpcCredentials.NewClientTLSFromFile(zbRPCCert, "")
	if err != nil {
		log.Fatalf("Unable to create TLS credentials from file (%s), should be a fullchain.pem type of certificate: %s", zbRPCCert, err)
	}
	log.Printf("Gateway: Establishing connection with zbCtrl gRPC at %s", zbRPCAddr)
	conn, err := grpc.Dial(zbRPCAddr, grpc.WithTransportCredentials(creds))
	if err != nil {
		log.Fatalf("Unable to connect to zbCtrl gRPC channel at %s: %s", zbRPCAddr, err)
	}
	ctrl := pb.NewZBCtrlClient(conn)
	log.Printf("Gateway: Connection established, zbCtrl client ready")

	g = &gateway{
		state:        zbState{},
		updateOk:     false,
		updateStatus: "000: Not started yet",
		updateTime:   0,
		zbRPCConn:    conn,
		zbRPCKey:     zbRPCKey,
		zbCtrl:       ctrl,
		running:      true,
	}

	// Periodic update of stored state
	go func() {
		for g.running {
			g.updateState()
			time.Sleep(updatePeriod)
		}
	}()
	return
}

func (g *gateway) Close() {
	g.running = false
	g.zbRPCConn.Close()
}

func (g *gateway) updateState() error {
	ctx, cancel := context.WithTimeout(context.Background(), zbRPCTimeoutGet)
	defer cancel()
	req := pb.GetStateRequest{Key: g.zbRPCKey}
	res, err := g.zbCtrl.GetState(ctx, &req)
	g.mu.Lock()
	defer g.mu.Unlock()
	if err != nil {
		errCode := grpcStatus.Code(err)
		g.updateOk = false
		g.updateStatus = fmt.Sprintf("gateway.updateState: ERROR calling getState zbCtrl RPC: #%d[%s] %s", errCode, errCode.String(), err)
		log.Println(g.updateStatus)
		return &ZbRCPError{g.updateStatus}
	}
	err = json.Unmarshal([]byte(res.GetState()), &g.state)
	if err != nil {
		g.updateOk = false
		g.updateStatus = fmt.Sprintf("gateway.updateState: ERROR decoding zbCtrl JSON response: %s", err)
		log.Println(g.updateStatus)
		return &ZbRCPError{g.updateStatus}
	}
	g.updateOk = true
	g.updateStatus = "OK"
	g.updateTime = time.Now().Unix()
	return nil
}

type apiState struct {
	Zigbee       zbState `json:"zigbee"`
	UpdateOk     bool    `json:"updateOk"`
	UpdateStatus string  `json:"updateStatus"`
	UpdateTime   int64   `json:"updateTime"`
}

func (g *gateway) GetState() apiState {
	g.mu.RLock()
	defer g.mu.RUnlock()
	return apiState{g.state.Copy(), g.updateOk, g.updateStatus, g.updateTime}
}

func (g *gateway) SetState(newState zbState) error {
	// TODO: check that newState is well formed
	ctx, cancel := context.WithTimeout(context.Background(), zbRPCTimeoutSet)
	defer cancel()
	newStateJson, err := json.Marshal(&newState)
	if err != nil {
		msg := fmt.Sprintf("gateway.SetState: ERROR encoding newState to JSON: %s", err)
		log.Println(msg)
		return &ZbRCPError{msg}
	}
	req := pb.SetStateRequest{Key: g.zbRPCKey, State: string(newStateJson)}
	res, err := g.zbCtrl.SetState(ctx, &req)
	if err != nil {
		msg := fmt.Sprintf("gateway.SetState: ERROR calling setState zbCtrl gRPC: %s", err)
		log.Println(msg)
		return &ZbRCPError{msg}
	}
	if !res.GetSuccess() {
		msg := "gateway.SetState: ERROR calling setState zbCtrl gRPC: unknown error (no success)"
		log.Println(msg)
		return &ZbRCPError{msg}
	}
	return g.updateState()
}
