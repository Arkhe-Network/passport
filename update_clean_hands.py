import sys

filename = "node/passport_gateway.py"

with open(filename, "r") as f:
    content = f.read()

find_str = """    async def verify_node_access(self, address: str) -> bool:
        \"\"\"Um endereço pode operar um nó se for humano.\"\"\"
        return await self.verify_dao_voter(address)"""

replace_str = """    async def verify_node_access(self, address: str) -> bool:
        \"\"\"Um endereço pode operar um nó se for humano e possuir Proof of Clean Hands (957).\"\"\"
        proof = await self.is_human(address)
        if not proof.is_human:
            return False

        # Proof of Clean Hands (sanctions/PEP) for AGI-Telcom
        return "CleanHands" in proof.stamps"""

content = content.replace(find_str, replace_str)

with open(filename, "w") as f:
    f.write(content)
