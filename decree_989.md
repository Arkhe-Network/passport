# decree_989.md

# Decreto Canônico 989.x — PASSPORT-GATEWAY

**Arquiteto ORCID:** 0009-0005-2697-4668
**Data:** 2026-05-30
**Era:** 9 (Apeiron / Meta)
**Deidades:** Themis (justiça), Athena (sabedoria), Hephaestus (forja on-chain)

---

## I. Proclamação

Pelo presente decreto, é canonizado o Substrato **989.x — PASSPORT-GATEWAY**, um portal multi-fonte de verificação de humanidade para a ARKHE Code Cathedral. A Catedral, em sua marcha rumo à Theosis, deve distinguir o joio do trigo: a governança (979) e a própria malha (972) não podem ser corrompidas por agentes sintéticos maliciosos. O Passport Gateway responde a essa necessidade com três camadas de verificação:

1. **Sign Protocol / EAS na Base:** A prova on-chain mais forte, materializada como uma attestation `isHuman` no Ethereum Attestation Service.
2. **Gitcoin Passport:** O scorer descentralizado que agrega dezenas de stamps (KYC, biometria, atividade Web3) e fornece um score de humanidade.
3. **ORCID:** A identidade acadêmica global, garantindo que pesquisadores verificados possuam humanidade implícita.

Cada verificação é ancorada na TemporalChain (923) e assinada pelo Arquiteto, tornando-se parte do registro imutável da Catedral. A API expõe endpoints para que a DAO possa exigir prova de humanidade para votar, e para que os operadores de nós da malha possam validar seu próprio acesso.

---

## II. Esquema Canônico

O esquema YAML associado (`passport_schema.yaml`) define os parâmetros, cross-links e dependências externas do substrato. Ele é parte integrante deste decreto.

---

## III. Integração com a Catedral

| Substrato | Papel |
|-----------|-------|
| **979 (DAO)** | Exige `verify_dao_voter(address)` antes de aceitar votos. |
| **972 (Global Mesh)** | Exige `verify_node_access(address)` para novos operadores de nó. |
| **954 (Axiarchy)** | Valida eticamente as fontes de verificação; nenhuma fonte pode violar P1-P7. |
| **982 (ORCID)** | Fornece fallback de identidade acadêmica. |
| **983 (API Gateway)** | Expõe `/v1/identity/passport`, `/v1/dao/verify-voter`, `/v1/mesh/verify-node`. |
| **923 (TemporalChain)** | Ancora cada prova de humanidade com seal. |
| **976 (Chainlink)** | Pode ser usado para verificar dados off-chain das stamps (ex: AML). |

---

## IV. Código e Repositório

O código-fonte do Passport Gateway reside no arquivo `node/passport_gateway.py` e está disponível no repositório público:
**[Arkhe-Network/passport](https://github.com/Arkhe-Network/passport)**

---

## V. Selo e Assinatura

Este decreto é selado com o ORCID do Arquiteto e registrado na TemporalChain.

```
arkhe > DECRETO 989.x — PUBLICADO
arkhe > Repo: https://github.com/Arkhe-Network/passport
arkhe > ODÔMETRO: ∞.Ω.∇+++.989.x.2
arkhe > A Catedral agora tem olhos. E ela vê apenas humanos.
```

ψ — Themis ergue a balança. Athena tece a sabedoria. Hephaestus forja o selo.
O Portão está aberto, mas somente àqueles que provam sua humanidade.
