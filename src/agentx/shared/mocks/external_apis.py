"""Mock external API tools for demo pipeline."""

FUND_MASTER = {
    "INF109K01VQ1": {"name": "HDFC Equity Fund", "nav": 89.45},
    "SG9999012345": {"name": "Apex SG Fund", "nav": 12.14},
}

INVESTOR_ACCOUNTS = {
    "INV-8847291": {"party": "Priya Sharma", "active": True},
    "INV-3928471": {"party": "Rajesh Kumar", "active": True},
    "INV-SG-4421": {"party": "Tan Wei Ming", "active": True},
}

AML_FLAGS = {"Global Pension Fund": "enhanced_dd"}


async def fund_lookup(isin: str) -> dict:
    return FUND_MASTER.get(isin, {})


async def investor_verify(account_id: str) -> dict:
    return INVESTOR_ACCOUNTS.get(account_id, {"active": False})


async def aml_screen(party: str) -> dict:
    flag = AML_FLAGS.get(party)
    return {"clear": flag is None, "hold": flag}


async def dispatch_ta(instruction_id: str) -> dict:
    return {"ack": True, "system": "TA", "ref": f"TA-{instruction_id[-4:]}"}


async def dispatch_fa(instruction_id: str) -> dict:
    return {"ack": True, "system": "FA", "ref": f"FA-{instruction_id[-4:]}"}


async def dispatch_is(instruction_id: str) -> dict:
    return {"ack": True, "system": "IS", "ref": f"IS-{instruction_id[-4:]}"}


async def dispatch_rtas(instruction_id: str) -> dict:
    return {"ack": True, "system": "RTAS", "ref": f"RTAS-{instruction_id[-4:]}"}


async def dispatch_vital(instruction_id: str) -> dict:
    return {"ack": True, "system": "ViTAL", "ref": f"ViTAL-{instruction_id[-4:]}"}


async def dispatch_rfas(instruction_id: str) -> dict:
    return {"ack": True, "system": "RFAS", "ref": f"RFAS-{instruction_id[-4:]}"}


async def fetch_settlement(instruction_id: str, expected: float) -> dict:
    if instruction_id == "INS-7844201":
        return {"matched": False, "expected": expected, "actual": expected - 50}
    return {"matched": True, "expected": expected, "actual": expected, "ref": f"SET-{instruction_id[-4:]}"}
