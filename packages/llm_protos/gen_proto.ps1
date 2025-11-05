# Clean any existing versions so generation definitely uses 5.x
python -m pip uninstall -y protobuf googleapis-common-protos grpcio-tools

# Install compatible toolchain
python -m pip install -U grpcio-tools==1.66.2 protobuf==5.29.5

# Clean & prep output dirs
Remove-Item -Recurse -Force .\src\llmruntime\v1  -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force .\src\llmruntime\v1 | Out-Null
New-Item -ItemType File .\src\llmruntime\__init__.py, .\src\llmruntime\v1\__init__.py | Out-Null

# Generate stubs (proto must have: syntax="proto3"; package llmruntime.v1;)
python -m grpc_tools.protoc `
  -I protos `
  --python_out=src `
  --grpc_python_out=src `
  protos/llmruntime/v1/llm.proto

Write-Host "Stubs generated to src/llmruntime/v1"
