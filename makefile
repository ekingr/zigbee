# Source
srcCtrl := controller
srcGway := gateway
srcFrnt := frontend
srcCfg := cfg
srcProto := proto
# Distribution
distCtrl := dist/zbCtrl
distGway := dist/zbGway
distFrnt := dist/zbGway/www
# Utils
deployCtrl := ./deploy-ctrl
deployGway := ./deploy-gway
venv := env
python := $(venv)/bin/python
pip := $(python) -m pip
export PATH := ${PATH}:/home/xxx/go/bin
babelInstall := node_modules/@babel/cli/bin/babel.js
babel := npx babel
sass := sass

.PHONY: all\
		prep\
		ctrl ctrlPb ctrlBin ctrlCfg\
		gway gwayPb gwayBin gwayCfg\
		frnt\
		install-ctrl_DEV install-ctrl_PROD\
		update-ctrl_DEV update-ctrl_PROD\
		install-gway_DEV install-gway_PROD\
		update-gway_DEV update-gway_PROD\
		update-frnt_DEV update-frnt_PROD


# ALL
all: prep ctrl gway frnt


# Preparation
prep: $(python) | $(distCtrl) $(distGway) $(distFrnt) $(babelInstall)

$(distCtrl) $(distGway) $(distFrnt):
	mkdir -p "$@"

$(python):
	python3.11 -m venv $(venv)
	$(pip) install --upgrade pip
	$(pip) install zigpy
	$(pip) install zigpy-znp
	$(pip) install pysqlite3-binary
	$(pip) install grpcio
	$(pip) install grpcio-tools

$(babelInstall):
	npm install --save-dev @babel/core @babel/cli
	npm install --save-dev @babel/preset-env
	npm install --save-dev @babel/preset-react
	npm install --save-dev @babel/preset-stage-2


# Controller
ctrl: ctrlPb ctrlBin ctrlCfg

# Controller: protobuf source files
ctrlPb: $(addprefix $(srcCtrl)/,\
		zbCtrl_pb2.py\
		zbCtrl_pb2.pyi\
		zbCtrl_pb2_grpc.py)

$(srcCtrl)/zbCtrl_pb2.py: $(srcProto)/zbCtrl.proto
	$(python) -m grpc_tools.protoc --proto_path="$(srcProto)" --python_out="$(srcCtrl)" --pyi_out="$(srcCtrl)" --grpc_python_out="$(srcCtrl)" "$^"

# Controller: binaries (actually python scripts)
ctrlBin: $(addprefix $(distCtrl)/,\
			server.py\
			controller.py\
			listener.py\
			zigbee.py\
			zbCtrl_pb2.py\
			zbCtrl_pb2.pyi\
			zbCtrl_pb2_grpc.py)

$(distCtrl)/%.py: $(srcCtrl)/%.py
	cp "$^" "$@"

$(distCtrl)/%.pyi: $(srcCtrl)/%.pyi
	cp "$^" "$@"

# Controller: configuration
ctrlCfg: $(addprefix $(distCtrl)/,\
			ctrl-init_systemd_DEV.conf\
			ctrl-init_systemd_PROD.conf\
			ctrl-init_upstart_DEV.conf\
			ctrl-init_upstart_PROD.conf\
			rpcKey_DEV.pem\
			rpcFullchain_DEV.pem\
			rpcKey_PROD.pem\
			rpcFullchain_PROD.pem\
			zigpy.db)

$(distCtrl)/ctrl-init_%.conf: $(srcCfg)/ctrl-init_%.conf
	cp "$^" "$@"

$(distCtrl)/rpcKey_DEV.pem $(distCtrl)/rpcFullchain_DEV.pem:
	openssl req -x509 -nodes -sha256 -days 3650 -newkey rsa:2048 -keyout "$(@D)/rpcKey_DEV.pem" -out "$(@D)/rpcFullchain_DEV.pem" -subj "/C=FR/ST=Paris/L=Paris/O=Domotique/OU=zbCtrl/CN=zbctrl.local/emailAddress=postmaster@local" -addext "subjectAltName = DNS:zbctrl.local"

$(distCtrl)/rpcKey_PROD.pem $(distCtrl)/rpcFullchain_PROD.pem:
	openssl req -x509 -nodes -sha256 -days 3650 -newkey rsa:2048 -keyout "$(@D)/rpcKey_PROD.pem" -out "$(@D)/rpcFullchain_PROD.pem" -subj "/C=FR/ST=Paris/L=Paris/O=Domotique/OU=zbCtrl/CN=zbctrl.my.example.com/emailAddress=postmaster@my.example.com" -addext "subjectAltName = DNS:zbctrl.my.example.com"

$(distCtrl)/zigpy.db: $(srcCfg)/zigpy.db
	cp "$^" "$@"


# Gateway
gway: gwayPb gwayBin gwayCfg 

# Gateway: protobuf source files
gwayPb: $(addprefix $(srcGway)/,\
		proto/zbCtrl.pb.go\
		proto/zbCtrl_grpc.pb.go)

$(srcGway)/proto/zbCtrl.pb.go: $(srcProto)/zbCtrl.proto
	protoc --go_out="$(srcGway)" --go_opt=paths=source_relative --go-grpc_out="$(srcGway)" --go-grpc_opt=paths=source_relative "$^"

# Gateway: binaries
gwayBin: $(addprefix $(distGway)/,\
			zbGateway_amd64\
			zbGateway_arm64\
			zbGateway_armv6)

$(distGway)/zbGateway_amd64: $(srcGway)/*.go
	cd "$(srcGway)/"; go mod tidy
	cd "$(srcGway)/"; go fmt
	cd "$(srcGway)/"; go build -o "../$@"

$(distGway)/zbGateway_arm64: $(srcGway)/*.go
	cd "$(srcGway)/"; go mod tidy
	cd "$(srcGway)/"; go fmt
	cd "$(srcGway)/"; GOOS=linux GOARCH=arm64 go build -o "../$@"

$(distGway)/zbGateway_armv6: $(srcGway)/*.go
	cd "$(srcGway)/"; go mod tidy
	cd "$(srcGway)/"; go fmt
	cd "$(srcGway)/"; GOOS=linux GOARCH=arm GOARM=6 go build -o "../$@"

# Gateway: configuration
gwayCfg: $(addprefix $(distGway)/,\
			gway-config.json\
			gway-init_systemd_DEV.conf\
			gway-init_systemd_PROD.conf\
			gway-init_upstart_DEV.conf\
			gway-init_upstart_PROD.conf\
			rpcFullchain_DEV.pem\
			rpcFullchain_PROD.pem)

$(distGway)/gway-init_%.conf: $(srcCfg)/gway-init_%.conf
	cp "$^" "$@"

$(distGway)/%.pem: $(distCtrl)/%.pem
	cp "$^" "$@"

$(distGway)/gway-config.json: $(srcCfg)/gway-config.json
	cp "$^" "$@"


# Frontend
frnt: $(addprefix $(distFrnt)/,\
		index.html\
		zigbee.js\
		zigbee.css)

$(distFrnt)/%.html: $(srcFrnt)/%.html
	cp "$^" "$@"

$(distFrnt)/%.js: $(srcFrnt)/%.jsx
	#$(babel) --no-babelrc --presets=@babel/preset-env,@babel/preset-react --no-comments --minified "$<" -o "$@"
	$(babel) --no-babelrc --presets=@babel/preset-env,@babel/preset-react "$<" -o "$@"

$(distFrnt)/%.css: $(srcFrnt)/%.scss
	$(sass) --no-source-map "$<" "$@"


# Install / Update
install-ctrl_DEV: prep ctrl
	$(deployCtrl) INSTALL DEV

install-ctrl_PROD: prep ctrl
	$(deployCtrl) INSTALL PROD

update-ctrl_DEV: prep ctrl
	$(deployCtrl) UPDATE DEV

update-ctrl_PROD: prep ctrl
	$(deployCtrl) UPDATE PROD

install-gway_DEV: prep gway frnt
	$(deployGway) INSTALL DEV

install-gway_PROD: prep gway frnt
	$(deployGway) INSTALL PROD

update-gway_DEV: prep gway frnt
	$(deployGway) UPDATE DEV

update-gway_PROD: prep gway frnt
	$(deployGway) UPDATE PROD

update-frnt_DEV: prep frnt
	$(deployGway) UPDATE-FRONT DEV

update-frnt_PROD: prep frnt
	$(deployGway) UPDATE-FRONT PROD

