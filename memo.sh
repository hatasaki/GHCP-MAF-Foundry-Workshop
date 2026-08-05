RG="20260805-ghcp-maf-fdry-ws"   # 例: rg-taro1111
ACCOUNT_NAME="ws-fdry-zukako"
PROJECT_NAME="proj-ghcpws"
MY_ID=$(az ad signed-in-user show --query id -o tsv)

ACCOUNT_ID=$(az cognitiveservices account show -g "$RG" --name "$ACCOUNT_NAME" --query id -o tsv)
PROJECT_ID="${ACCOUNT_ID}/projects/${PROJECT_NAME}"

az role assignment create --role "eadc314b-1a2d-4efa-be10-5d325db5065e" --assignee-object-id "$MY_ID" --assignee-principal-type User --scope "$PROJECT_ID"