import sys

filename = "node/passport_gateway.py"

with open(filename, "r") as f:
    content = f.read()

import1 = "from datetime import datetime, timezone"
import2 = "from datetime import datetime, timezone\nimport time"

content = content.replace(import1, import2)

init1 = """    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.temporalchain_endpoint = os.environ.get(
            "TEMPORALCHAIN_ENDPOINT", "https://api.arkhe-catedral.org/v1/anchor"
        )"""

init2 = """    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.temporalchain_endpoint = os.environ.get(
            "TEMPORALCHAIN_ENDPOINT", "https://api.arkhe-catedral.org/v1/anchor"
        )
        # Cache distribuído simulado (TTL 300s)
        self.cache = {}
        self.cache_ttl = 300"""

content = content.replace(init1, init2)

is_human1 = """    async def is_human(self, address: str) -> HumanityProof:
        \"\"\"Determina se um endereço é humano com base nas fontes configuradas.\"\"\"
        # 1. Sign Protocol"""

is_human2 = """    async def is_human(self, address: str) -> HumanityProof:
        \"\"\"Determina se um endereço é humano com base nas fontes configuradas.\"\"\"
        # Check cache
        cached = self.cache.get(address)
        if cached:
            proof, timestamp = cached
            if time.time() - timestamp < self.cache_ttl:
                return proof

        proof = await self._is_human_internal(address)
        self.cache[address] = (proof, time.time())
        return proof

    async def _is_human_internal(self, address: str) -> HumanityProof:
        # 1. Sign Protocol"""

content = content.replace(is_human1, is_human2)

with open(filename, "w") as f:
    f.write(content)
