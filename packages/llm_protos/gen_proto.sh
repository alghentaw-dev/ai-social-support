python -m pip install -q grpcio-tools
rm -rf src/llmruntime/v1
mkdir -p src/llmruntime/v1
: > src/llmruntime/__init__.py
: > src/llmruntime/v1/__init__.py

python -m grpc_tools.protoc \
  -I protos \
  --python_out=src \
  --grpc_python_out=src \
  protos/llmruntime/v1/llm.proto

echo "Stubs generated to src/llmruntime/v1"
