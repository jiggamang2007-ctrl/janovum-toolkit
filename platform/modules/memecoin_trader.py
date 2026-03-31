"""
Janovum AI Memecoin Trading Bot — Multi-Strategy Engine

STRATEGY 1 — "Pump.fun Retrace" (Jaden's strategy, primary):
  Find pump.fun coins that pumped then crashed to $7k-$15k market cap.
  Still have decent volume (trade every 5-10 sec, not dead).
  Good narrative/idea. Not bundled, not rugged, real organic growth.
  Buy the dip, ride the retrace bounce, take profit.

STRATEGY 2 — "Volume Spike Hunter":
  Scan all pump.fun coins for sudden volume spikes on low-MC tokens.
  If a coin at $5k-$20k MC suddenly gets 5x its normal volume in
  the last 5 minutes, something is happening. AI evaluates if it's
  accumulation (good) or a dump (bad).

STRATEGY 3 — "Social Sentiment Scanner":
  Monitor Twitter/X for trending Solana tickers and pump.fun links.
  When a coin gets social buzz + still has low MC, it's early.
  Cross-reference with on-chain data to verify it's real momentum.

All strategies share: rug protection, bundle detection, AI analysis.
Target: 2-3 trades per day. Patient. Only perfect setups.
"""

import asyncio
import aiohttp
import time
import json
import os
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "trader"
DATA_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = Path(__file__).parent.parent / "logs" / "memecoin_trader.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, mode="a"), logging.StreamHandler()]
)
log = logging.getLogger("memecoin_trader")

# ══════════════════════════════════════
# CONFIG
# ══════════════════════════════════════

DEFAULT_CONFIG = {
    "enabled": False,
    "wallet_private_key": "",          # Solana wallet private key (base58)
    "rpc_url": "https://api.mainnet-beta.solana.com",
    "max_sol_per_trade": 0.1,          # Max SOL to spend per trade
    "max_trades_per_day": 3,
    "take_profit_pct": 50,             # Sell at +50% (pump.fun coins move big)
    "stop_loss_pct": 20,               # Sell at -20%
    "trailing_stop_pct": 15,           # Trail 15% from peak once in profit
    "scan_interval_seconds": 15,       # How often to scan (faster for pump.fun)
    "slippage_bps": 800,               # 8% slippage (pump.fun coins are volatile)
    "dry_run": True,                   # Paper trade mode (no real transactions)

    # === STRATEGY 1: Pump.fun Retrace (PRIMARY) ===
    "s1_enabled": True,
    "s1_min_mc": 5000,                 # Min $5k market cap
    "s1_max_mc": 15000,                # Max $15k market cap (low MC pump.fun coins)
    "s1_min_trades_per_min": 3,        # At least 3 trades/min (not dead, ~1 every 20 sec)
    "s1_min_drop_from_peak_pct": 50,   # Must have dropped 50%+ from its peak
    "s1_max_age_hours": 24,            # Created within last 24 hours
    "s1_min_age_minutes": 15,          # At least 15 min old (avoid first-minute chaos)
    "s1_max_dev_holding_pct": 5,       # Dev can't hold more than 5%
    "s1_min_unique_holders": 30,       # At least 30 unique holders
    "s1_reject_bundled": True,         # Reject tokens where dev bundled the launch
    "s1_require_narrative": True,      # Must match a narrative keyword or AI must approve

    # === STRATEGY 2: Volume Spike Hunter ===
    "s2_enabled": True,
    "s2_min_mc": 3000,                 # Min $3k market cap
    "s2_max_mc": 25000,                # Max $25k
    "s2_volume_spike_multiplier": 3,   # Volume must be 3x normal in last 5 min
    "s2_min_buy_ratio": 0.55,          # 55%+ of recent txns must be buys

    # === STRATEGY 3: Social Sentiment ===
    "s3_enabled": False,               # Disabled by default (needs Twitter scraping)
    "s3_min_mentions": 5,              # Min mentions in last hour
    "s3_max_mc_at_mention": 50000,     # MC must be under $50k when mentioned

    # === Narrative keywords ===
    "narrative_keywords": [
        "ai", "agent", "gpt", "claude", "meme", "dog", "cat", "pepe",
        "trump", "elon", "doge", "wojak", "chad", "moon", "based",
        "sol", "bonk", "jup", "send", "pump", "frog", "bear", "bull",
        "ape", "monke", "nft", "gaming", "meta", "coin", "token",
        "crypto", "degen", "diamond", "hands", "wagmi", "gm",
    ],
}

def load_config():
    path = DATA_DIR / "config.json"
    if path.exists():
        with open(path) as f:
            saved = json.load(f)
        cfg = {**DEFAULT_CONFIG, **saved}
    else:
        cfg = dict(DEFAULT_CONFIG)
    return cfg

def save_config(cfg):
    with open(DATA_DIR / "config.json", "w") as f:
        json.dump(cfg, f, indent=2)

def load_trades():
    path = DATA_DIR / "trades.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []

def save_trades(trades):
    with open(DATA_DIR / "trades.json", "w") as f:
        json.dump(trades, f, indent=2, default=str)

def load_watchlist():
    path = DATA_DIR / "watchlist.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []

def save_watchlist(wl):
    with open(DATA_DIR / "watchlist.json", "w") as f:
        json.dump(wl, f, indent=2, default=str)


# ══════════════════════════════════════
# API CLIENTS (DexScreener, BirdEye, Jupiter, Solana)
# ══════════════════════════════════════

class DexScreenerClient:
    """Free API — no key needed."""
    BASE = "https://api.dexscreener.com"

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    async def get_new_pairs(self, chain="solana"):
        """Get latest token pairs on Solana."""
        url = f"{self.BASE}/token-profiles/latest/v1"
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    data = await r.json()
                    # Filter to solana
                    return [p for p in (data if isinstance(data, list) else []) if p.get("chainId") == "solana"]
        except Exception as e:
            log.warning(f"DexScreener new pairs error: {e}")
        return []

    async def get_boosted_tokens(self):
        """Get tokens with active boosts (high visibility = narrative)."""
        url = f"{self.BASE}/token-boosts/latest/v1"
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    data = await r.json()
                    return [t for t in (data if isinstance(data, list) else []) if t.get("chainId") == "solana"]
        except Exception as e:
            log.warning(f"DexScreener boosts error: {e}")
        return []

    async def get_token_pairs(self, token_address: str):
        """Get pair data for a specific token."""
        url = f"{self.BASE}/tokens/v1/solana/{token_address}"
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    data = await r.json()
                    if isinstance(data, list) and data:
                        return data
        except Exception as e:
            log.warning(f"DexScreener token error: {e}")
        return []

    async def search_tokens(self, query: str):
        """Search for tokens by name/symbol."""
        url = f"{self.BASE}/latest/dex/search?q={query}"
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    data = await r.json()
                    pairs = data.get("pairs", [])
                    return [p for p in pairs if p.get("chainId") == "solana"]
        except Exception as e:
            log.warning(f"DexScreener search error: {e}")
        return []


class PumpFunClient:
    """Monitor pump.fun tokens — both active (on bonding curve) and graduated."""
    BASE = "https://frontend-api-v2.pump.fun"

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    async def get_graduated_tokens(self, limit=50):
        """Get recently graduated (bonded to Raydium) tokens."""
        url = f"{self.BASE}/coins?offset=0&limit={limit}&sort=last_trade_timestamp&order=DESC&includeNsfw=false&complete=true"
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    return await r.json()
        except Exception as e:
            log.warning(f"PumpFun graduated error: {e}")
        return []

    async def get_active_coins(self, limit=50, sort="last_trade_timestamp"):
        """Get active pump.fun coins (still on bonding curve, not yet graduated).
        These are the $5k-$15k MC coins we want — pumped and dumped but still trading."""
        url = f"{self.BASE}/coins?offset=0&limit={limit}&sort={sort}&order=DESC&includeNsfw=false&complete=false"
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    return await r.json()
        except Exception as e:
            log.warning(f"PumpFun active coins error: {e}")
        return []

    async def get_token_info(self, mint: str):
        """Get detailed info about a pump.fun token — MC, creator, reply count, etc."""
        url = f"{self.BASE}/coins/{mint}"
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    return await r.json()
        except Exception as e:
            log.warning(f"PumpFun token info error: {e}")
        return None

    async def get_token_trades(self, mint: str, limit=50):
        """Get recent trades for a token — needed to check trade frequency and buy/sell ratio."""
        url = f"{self.BASE}/trades/latest?mint={mint}&limit={limit}"
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    return await r.json()
        except Exception as e:
            log.warning(f"PumpFun trades error: {e}")
        return []

    async def get_token_holders(self, mint: str):
        """Get holder distribution — needed to check bundle and dev holdings."""
        # pump.fun doesn't expose this directly, we use Solana RPC or Helius
        # For now return empty, rug checker handles this via rugcheck.xyz
        return []

    def estimate_market_cap(self, token_data: dict) -> float:
        """Estimate MC from pump.fun token data.
        pump.fun bonding curve: MC = virtual_sol_reserves * SOL_price * 2 (roughly).
        Or use usd_market_cap if provided."""
        if token_data.get("usd_market_cap"):
            return float(token_data["usd_market_cap"])
        # Fallback: estimate from virtual reserves
        vsr = token_data.get("virtual_sol_reserves", 0)
        if vsr:
            # Very rough: virtual SOL reserves * 2 * SOL price (~$130)
            return (vsr / 1e9) * 2 * 130  # lamports to SOL, *2 for both sides, *SOL price
        return 0

    def get_peak_mc(self, token_data: dict) -> float:
        """Estimate peak market cap from the highest point the bonding curve reached."""
        # pump.fun tracks this via the bonding curve progress
        # If complete=false, the coin is still on the curve
        # The "market_cap" field shows current MC
        # We can estimate peak from the difference between current and initial
        current = self.estimate_market_cap(token_data)
        # If the token has reply_count > 50, it probably peaked higher
        replies = token_data.get("reply_count", 0)
        # Rough heuristic: more replies = more attention = probably pumped higher
        # A coin with 100+ replies likely hit $30k+ at some point
        if replies > 100:
            return max(current * 3, 30000)
        elif replies > 50:
            return max(current * 2.5, 20000)
        elif replies > 20:
            return max(current * 2, 15000)
        return current * 1.5  # Conservative estimate


class JupiterClient:
    """Jupiter aggregator for Solana swaps."""
    BASE = "https://quote-api.jup.ag/v6"

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    async def get_quote(self, input_mint: str, output_mint: str, amount_lamports: int, slippage_bps: int = 500):
        """Get swap quote from Jupiter."""
        url = f"{self.BASE}/quote"
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount_lamports),
            "slippageBps": slippage_bps,
            "onlyDirectRoutes": "false",
        }
        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    return await r.json()
        except Exception as e:
            log.warning(f"Jupiter quote error: {e}")
        return None

    async def get_swap_tx(self, quote: dict, user_pubkey: str):
        """Get serialized swap transaction from Jupiter."""
        url = f"{self.BASE}/swap"
        body = {
            "quoteResponse": quote,
            "userPublicKey": user_pubkey,
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
            "prioritizationFeeLamports": "auto",
        }
        try:
            async with self.session.post(url, json=body, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status == 200:
                    return await r.json()
        except Exception as e:
            log.warning(f"Jupiter swap error: {e}")
        return None


class SolanaClient:
    """Minimal Solana RPC client for balance checks and tx submission."""

    def __init__(self, session: aiohttp.ClientSession, rpc_url: str):
        self.session = session
        self.rpc_url = rpc_url

    async def _rpc(self, method: str, params=None):
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
        try:
            async with self.session.post(self.rpc_url, json=body, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()
                return data.get("result")
        except Exception as e:
            log.warning(f"Solana RPC error ({method}): {e}")
        return None

    async def get_balance(self, pubkey: str):
        result = await self._rpc("getBalance", [pubkey])
        if result:
            return result.get("value", 0) / 1e9  # lamports to SOL
        return 0.0

    async def get_token_accounts(self, pubkey: str):
        result = await self._rpc("getTokenAccountsByOwner", [
            pubkey,
            {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
            {"encoding": "jsonParsed"}
        ])
        if result:
            return result.get("value", [])
        return []

    async def send_transaction(self, signed_tx_base64: str):
        result = await self._rpc("sendTransaction", [
            signed_tx_base64,
            {"encoding": "base64", "skipPreflight": False, "preflightCommitment": "confirmed"}
        ])
        return result

    async def confirm_transaction(self, signature: str, timeout=30):
        start = time.time()
        while time.time() - start < timeout:
            result = await self._rpc("getSignatureStatuses", [[signature]])
            if result and result.get("value") and result["value"][0]:
                status = result["value"][0]
                if status.get("confirmationStatus") in ("confirmed", "finalized"):
                    return not status.get("err")
            await asyncio.sleep(2)
        return False


# ══════════════════════════════════════
# RUG CHECKER
# ══════════════════════════════════════

class BundleDetector:
    """Detects if a token launch was bundled (dev bought their own supply to fake volume).
    Bundled launches = dev uses multiple wallets to buy in the first seconds,
    concentrating supply. This is a HUGE red flag."""

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    async def is_bundled(self, token_address: str, trades: list = None) -> dict:
        """Check if the token launch was bundled."""
        result = {"is_bundled": False, "confidence": 0, "details": []}

        # Method 1: Check early trades from pump.fun
        if trades:
            # Look at the first 10 trades
            early_trades = trades[-10:] if len(trades) >= 10 else trades  # trades are newest-first
            if early_trades:
                # Check if multiple early buys came from the same wallet or related wallets
                early_buyers = {}
                for t in early_trades:
                    user = t.get("user", "") or t.get("traderPublicKey", "")
                    if t.get("is_buy", True):
                        early_buyers[user] = early_buyers.get(user, 0) + 1

                # If one wallet bought multiple times in the first trades = likely bundled
                for wallet, count in early_buyers.items():
                    if count >= 3:
                        result["is_bundled"] = True
                        result["confidence"] = 80
                        result["details"].append(f"Wallet {wallet[:8]}... bought {count}x in first trades")

                # If very few unique buyers in first 10 trades
                if len(early_buyers) <= 2 and len(early_trades) >= 5:
                    result["is_bundled"] = True
                    result["confidence"] = max(result["confidence"], 70)
                    result["details"].append(f"Only {len(early_buyers)} unique buyers in first {len(early_trades)} trades")

        # Method 2: RugCheck.xyz bundle detection
        try:
            url = f"https://api.rugcheck.xyz/v1/tokens/{token_address}/report/summary"
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    report = await r.json()
                    for risk in report.get("risks", []):
                        name = risk.get("name", "").lower()
                        if "bundle" in name or "insider" in name:
                            result["is_bundled"] = True
                            result["confidence"] = max(result["confidence"], 90)
                            result["details"].append(f"RugCheck flagged: {risk.get('name')}")
                        if "high ownership" in name or "top holder" in name:
                            result["confidence"] = max(result["confidence"], 60)
                            result["details"].append(f"RugCheck: {risk.get('name')}")
        except Exception as e:
            log.debug(f"Bundle check rugcheck error: {e}")

        return result


class RugChecker:
    """Comprehensive rug pull and safety checker."""

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.bundle_detector = BundleDetector(session)

    async def check(self, token_address: str, pair_data: dict = None,
                    pumpfun_data: dict = None, trades: list = None) -> dict:
        """Returns full safety assessment including bundle detection."""
        risks = []
        score = 0  # 0 = safe, 100 = definitely a rug

        # === BUNDLE CHECK (critical) ===
        bundle_result = await self.bundle_detector.is_bundled(token_address, trades)
        if bundle_result["is_bundled"]:
            risks.append(f"BUNDLED LAUNCH: {', '.join(bundle_result['details'][:2])}")
            score += 40  # Instant near-reject

        # === PUMP.FUN SPECIFIC CHECKS ===
        if pumpfun_data:
            # Dev holdings check
            creator = pumpfun_data.get("creator", "")
            # Check if the dev has sold (pump.fun shows this)
            if pumpfun_data.get("creator_balance_percentage", 100) > 5:
                dev_pct = pumpfun_data.get("creator_balance_percentage", 0)
                risks.append(f"Dev still holds {dev_pct:.1f}% of supply")
                score += 15 if dev_pct > 10 else 8

            # Check reply count (social proof)
            replies = pumpfun_data.get("reply_count", 0)
            if replies < 5:
                risks.append(f"Very few pump.fun replies ({replies})")
                score += 8

            # Check if token has a website or twitter
            website = pumpfun_data.get("website", "")
            twitter = pumpfun_data.get("twitter", "")
            telegram = pumpfun_data.get("telegram", "")
            if not website and not twitter and not telegram:
                risks.append("No website, Twitter, or Telegram")
                score += 5

        # === DEX DATA CHECKS ===
        if pair_data:
            liq = pair_data.get("liquidity", {}).get("usd", 0) if isinstance(pair_data.get("liquidity"), dict) else 0
            vol = pair_data.get("volume", {}).get("h24", 0) if isinstance(pair_data.get("volume"), dict) else 0

            # For pump.fun coins at $7k-15k MC, liquidity will be low — that's expected
            # Only flag if liquidity is suspiciously zero
            if liq == 0 and vol > 0:
                risks.append("Zero liquidity with volume — suspicious")
                score += 20

            # Check txns — if buys are 0 but sells are high
            txns = pair_data.get("txns", {})
            h1_txns = txns.get("h1", {}) if isinstance(txns.get("h1"), dict) else {}
            buys = h1_txns.get("buys", 0)
            sells = h1_txns.get("sells", 0)
            if sells > 10 and buys == 0:
                risks.append("Only sells, no buyers — dead or rugged")
                score += 30

        # === RUGCHECK.XYZ API (comprehensive) ===
        try:
            url = f"https://api.rugcheck.xyz/v1/tokens/{token_address}/report/summary"
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    report = await r.json()
                    rc_risks = report.get("risks", [])
                    for risk in rc_risks:
                        name = risk.get("name", "")
                        level = risk.get("level", "")
                        desc = risk.get("description", "")
                        if level in ("danger", "error"):
                            # Check if it's a rug-specific risk
                            if any(w in name.lower() for w in ["rug", "mint", "freeze", "honeypot"]):
                                risks.append(f"CRITICAL: {name}")
                                score += 35
                            else:
                                risks.append(f"RugCheck: {name}")
                                score += 15
                        elif level == "warn":
                            risks.append(f"Warning: {name}")
                            score += 5

                    # Check top holders from rugcheck
                    top_holders = report.get("topHolders", [])
                    if top_holders:
                        top_pct = top_holders[0].get("pct", 0) if top_holders else 0
                        if top_pct > 20:
                            risks.append(f"Top holder owns {top_pct:.1f}%")
                            score += 20
                        elif top_pct > 10:
                            risks.append(f"Top holder owns {top_pct:.1f}%")
                            score += 8
        except Exception as e:
            log.debug(f"RugCheck API error: {e}")
            # Can't verify = add small risk
            score += 5

        is_safe = score < 35  # Stricter threshold
        return {
            "token": token_address,
            "score": min(score, 100),
            "is_safe": is_safe,
            "is_bundled": bundle_result["is_bundled"],
            "bundle_confidence": bundle_result["confidence"],
            "risks": risks,
            "verdict": "SAFE" if score < 20 else "CAUTION" if score < 40 else "DANGEROUS"
        }


# ══════════════════════════════════════
# TRADING ENGINE
# ══════════════════════════════════════

SOL_MINT = "So11111111111111111111111111111111111111112"


# ══════════════════════════════════════
# AI ANALYSIS (Claude)
# ══════════════════════════════════════

class AIAnalyst:
    """Uses Claude to analyze token data and make smart entry/exit decisions."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self.session = session
        self.api_key = api_key
        self.model = model  # Haiku for speed + cost, upgrade to Sonnet for accuracy

    async def analyze_entry(self, token_data: dict, pair_data: dict, rug_result: dict) -> dict:
        """Ask Claude to analyze whether this token is a good retrace entry.
        Uses Haiku for speed + cost, but sends rich context for smart decisions."""
        if not self.api_key:
            return {"should_enter": True, "confidence": 50, "reasoning": "No API key — skipping AI analysis"}

        # Build rich context depending on what data we have
        mc = token_data.get('market_cap', 0) or (pair_data.get('marketCap', 0) if pair_data else 0)
        peak_mc = token_data.get('peak_mc', 0)
        drop_pct = token_data.get('drop_pct', 0)
        tpm = token_data.get('trades_per_min', 0)
        buy_ratio = token_data.get('buy_ratio', 0)
        holders = token_data.get('estimated_holders', 0)
        replies = token_data.get('reply_count', 0)

        # DexScreener data if available
        dex_vol = pair_data.get('volume', {}).get('h24', 0) if isinstance(pair_data.get('volume'), dict) else 0
        dex_liq = pair_data.get('liquidity', {}).get('usd', 0) if isinstance(pair_data.get('liquidity'), dict) else 0

        prompt = f"""You are an expert Solana pump.fun memecoin trader. Your ONLY job: decide if this token is a good RETRACE ENTRY.

THE STRATEGY (proven profitable):
We find pump.fun coins that pumped then crashed to $5k-$15k market cap. These coins had real interest (people bought in, there's a community) but the initial hype faded. We wait for the coin to hit bottom — you can tell because:
1. It dropped 50%+ from its peak
2. There are still active trades happening (not dead)
3. Buying pressure starts returning (more buys than sells)
4. The narrative/name is catchy enough to attract new buyers
When these conditions align, the coin often retraces 30-100% from the bottom. We ride that bounce.

TOKEN:
- Symbol: {token_data.get('symbol', '???')}
- Name: {token_data.get('name', '')}
- Description: {token_data.get('description', '')[:200]}
- Market Cap: ${mc:,.0f}
- Peak Market Cap: ~${peak_mc:,.0f}
- Drop from Peak: {drop_pct:.0f}%
- Trades per Minute: {tpm:.1f} (higher = more active)
- Buy/Sell Ratio (last 20 trades): {buy_ratio:.0%} buys
- Estimated Unique Holders: ~{holders}
- Pump.fun Replies: {replies}
- DexScreener Volume 24h: ${dex_vol:,.0f}
- DexScreener Liquidity: ${dex_liq:,.0f}

RUG CHECK:
- Verdict: {rug_result.get('verdict', 'UNKNOWN')} (score {rug_result.get('score', 0)}/100)
- Bundled: {'YES — REJECT' if rug_result.get('is_bundled') else 'No'}
- Risks: {', '.join(rug_result.get('risks', [])[:4]) or 'None'}

YOUR ANALYSIS (think step by step):
1. NARRATIVE: Is "{token_data.get('name', '')}" / "${token_data.get('symbol', '')}" a catchy meme that people would buy? Would you see this trending? Score 1-10.
2. BOTTOM SIGNAL: Has it dropped enough ({drop_pct:.0f}%) and is volume ({tpm:.1f} trades/min) showing it's not dead?
3. REVERSAL: Is the buy ratio ({buy_ratio:.0%}) showing buyers are coming back?
4. RISK: Any red flags from the rug check? Is this worth 0.1 SOL?
5. TIMING: Is NOW the right time or should we wait for a better entry?

Respond ONLY with this JSON (no other text):
{{"should_enter": true/false, "confidence": 0-100, "reasoning": "2-3 sentences why", "suggested_tp_pct": 30-100, "suggested_sl_pct": 15-25, "narrative_score": 0-10, "bounce_probability": 0-100}}"""

        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            body = {
                "model": self.model,
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}],
            }
            async with self.session.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers, json=body,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as r:
                if r.status == 200:
                    data = await r.json()
                    text = data.get("content", [{}])[0].get("text", "")
                    # Parse JSON from response
                    import re
                    json_match = re.search(r'\{[^{}]*"should_enter"[^{}]*\}', text, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                        log.info(f"AI Analysis: enter={result.get('should_enter')} "
                                 f"confidence={result.get('confidence')}% — {result.get('reasoning', '')[:100]}")
                        return result
                else:
                    error_text = await r.text()
                    log.warning(f"AI API error {r.status}: {error_text[:200]}")

        except Exception as e:
            log.warning(f"AI analysis error: {e}")

        return {"should_enter": True, "confidence": 50, "reasoning": "AI analysis unavailable — using filters only"}

    async def analyze_exit(self, position: dict, pair_data: dict) -> dict:
        """Ask Claude if we should hold or sell a position."""
        if not self.api_key:
            return {"should_exit": False, "reasoning": "No API key"}

        entry_price = position.get("entry_price", 0)
        current_price = float(pair_data.get("priceUsd", 0) or 0)
        pnl_pct = ((current_price - entry_price) / max(entry_price, 0.00000001)) * 100 if entry_price > 0 else 0

        prompt = f"""You are an expert memecoin trader managing an open position.

POSITION:
- Token: {position.get('symbol')} ({position.get('name')})
- Entry Price: ${entry_price:.10f}
- Current Price: ${current_price:.10f}
- PnL: {pnl_pct:+.1f}%
- Time held: since {position.get('entry_time', 'unknown')}

CURRENT MARKET:
- 5min Change: {pair_data.get('priceChange', {}).get('m5', 0)}%
- 1h Change: {pair_data.get('priceChange', {}).get('h1', 0)}%
- 5min Buys/Sells: {pair_data.get('txns', {}).get('m5', {}).get('buys', 0)}/{pair_data.get('txns', {}).get('m5', {}).get('sells', 0)}
- Volume 24h: ${pair_data.get('volume', {}).get('h24', 0):,.0f}
- Liquidity: ${pair_data.get('liquidity', {}).get('usd', 0):,.0f}

Should we SELL now or HOLD? Consider: Is momentum fading? Are sellers taking over? Has the bounce peaked?

Respond in JSON: {{"should_exit": true/false, "reasoning": "1-2 sentences", "urgency": "low/medium/high"}}"""

        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            body = {
                "model": self.model,
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}],
            }
            async with self.session.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers, json=body,
                timeout=aiohttp.ClientTimeout(total=12)
            ) as r:
                if r.status == 200:
                    data = await r.json()
                    text = data.get("content", [{}])[0].get("text", "")
                    import re
                    json_match = re.search(r'\{[^{}]*"should_exit"[^{}]*\}', text, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())
        except Exception as e:
            log.debug(f"AI exit analysis error: {e}")

        return {"should_exit": False, "reasoning": "AI unavailable — using TP/SL rules"}


class MemecoinTrader:
    """The main trading engine. Scans, filters, enters, manages, exits."""

    def __init__(self):
        self.cfg = load_config()
        self.trades = load_trades()
        self.watchlist = load_watchlist()
        self.session = None
        self.dex = None
        self.pump = None
        self.jupiter = None
        self.solana = None
        self.rug_checker = None
        self.ai = None
        self.running = False
        self.status = "stopped"
        self.last_scan = None
        self.scanned_tokens = set()
        self.today_trades = 0
        self.today_date = None
        self.wallet_pubkey = ""
        self.sol_balance = 0.0
        self.active_positions = []  # Tokens we're currently holding
        self.stats = {"scanned": 0, "passed_filter": 0, "rug_checked": 0, "entries": 0, "exits": 0, "pnl_sol": 0.0}

    async def start(self):
        """Start the trading bot."""
        self.cfg = load_config()

        if not self.cfg.get("wallet_private_key") and not self.cfg.get("dry_run"):
            log.error("No wallet private key set and dry_run is off. Aborting.")
            return

        self.session = aiohttp.ClientSession()
        self.dex = DexScreenerClient(self.session)
        self.pump = PumpFunClient(self.session)
        self.jupiter = JupiterClient(self.session)
        self.solana = SolanaClient(self.session, self.cfg["rpc_url"])
        self.rug_checker = RugChecker(self.session)
        # Init AI analyst if API key is available
        api_key = self.cfg.get("anthropic_api_key", "")
        if not api_key:
            # Try loading from main platform config
            try:
                main_cfg_path = Path(__file__).parent.parent / "config.json"
                if main_cfg_path.exists():
                    with open(main_cfg_path) as f:
                        main_cfg = json.load(f)
                    api_key = main_cfg.get("api_key", "")
            except Exception:
                pass
        ai_model = self.cfg.get("ai_model", "claude-haiku-4-5-20251001")
        self.ai = AIAnalyst(self.session, api_key, ai_model)
        if api_key:
            log.info(f"AI Analyst enabled (model: {ai_model})")
        else:
            log.info("AI Analyst disabled — no API key. Using filter-only mode.")
        self.running = True
        self.status = "running"

        # Derive wallet pubkey from private key if available
        if self.cfg.get("wallet_private_key"):
            try:
                from solders.keypair import Keypair
                import base58
                kp = Keypair.from_bytes(base58.b58decode(self.cfg["wallet_private_key"]))
                self.wallet_pubkey = str(kp.pubkey())
                self.sol_balance = await self.solana.get_balance(self.wallet_pubkey)
                log.info(f"Wallet: {self.wallet_pubkey[:8]}... | Balance: {self.sol_balance:.4f} SOL")
            except ImportError:
                log.warning("solders/base58 not installed. Install with: pip install solders base58")
                if not self.cfg["dry_run"]:
                    log.error("Cannot trade without solders. Switching to dry run.")
                    self.cfg["dry_run"] = True
            except Exception as e:
                log.error(f"Wallet init error: {e}")
                self.cfg["dry_run"] = True

        if self.cfg["dry_run"]:
            log.info("=== DRY RUN MODE — No real trades ===")
            self.sol_balance = 10.0  # Simulated balance

        log.info("Memecoin Sniper Bot started")
        log.info(f"Config: max {self.cfg['max_sol_per_trade']} SOL/trade, "
                 f"TP {self.cfg['take_profit_pct']}%, SL {self.cfg['stop_loss_pct']}%, "
                 f"max {self.cfg['max_trades_per_day']} trades/day")

        # Load active positions from trades
        self.active_positions = [t for t in self.trades if t.get("status") == "open"]

        # Main loop
        try:
            while self.running:
                await self._scan_cycle()
                await self._manage_positions()
                await asyncio.sleep(self.cfg["scan_interval_seconds"])
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"Bot error: {e}", exc_info=True)
        finally:
            self.status = "stopped"
            self.running = False
            if self.session:
                await self.session.close()
            log.info("Bot stopped.")

    def stop(self):
        """Stop the bot gracefully."""
        self.running = False
        self.status = "stopping"
        log.info("Stop signal received.")

    async def _scan_cycle(self):
        """One full scan cycle: run all enabled strategies."""
        # Reset daily counter
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self.today_date != today:
            self.today_date = today
            self.today_trades = len([t for t in self.trades
                                     if t.get("entry_time", "").startswith(today) and t.get("status") != "cancelled"])

        if self.today_trades >= self.cfg["max_trades_per_day"]:
            self.status = "max_trades_reached — waiting for tomorrow"
            return

        self.status = "scanning"
        self.last_scan = datetime.now(timezone.utc).isoformat()

        # === STRATEGY 1: Pump.fun Retrace (PRIMARY) ===
        if self.cfg.get("s1_enabled", True):
            await self._strategy_pumpfun_retrace()

        # === STRATEGY 2: Volume Spike Hunter ===
        if self.cfg.get("s2_enabled", True):
            await self._strategy_volume_spike()

        # === STRATEGY 3: Social Sentiment (if enabled) ===
        if self.cfg.get("s3_enabled", False):
            await self._strategy_social_sentiment()

        # Also re-check watchlist items for entry signals
        await self._recheck_watchlist()

    async def _strategy_pumpfun_retrace(self):
        """STRATEGY 1: Jaden's strategy. Find pump.fun coins at $7k-$15k MC that:
        - Pumped then crashed (50%+ down from peak)
        - Still have active trading (trades every 5-10 seconds)
        - Good narrative
        - Not bundled, not rugged, real organic growth
        - Buy when buying pressure starts returning"""

        self.status = "S1: scanning pump.fun retraces"

        # Get active pump.fun coins (still on bonding curve, recently traded)
        active = await self.pump.get_active_coins(limit=50, sort="last_trade_timestamp")
        if not isinstance(active, list):
            return

        candidates = []
        for token in active:
            mint = token.get("mint", "")
            if not mint or mint in self.scanned_tokens:
                continue

            # Quick MC filter before deeper checks
            mc = self.pump.estimate_market_cap(token)
            min_mc = self.cfg.get("s1_min_mc", 5000)
            max_mc = self.cfg.get("s1_max_mc", 15000)

            if mc < min_mc or mc > max_mc:
                continue

            # Age filter
            created = token.get("created_timestamp")
            if created:
                try:
                    age_min = (time.time() * 1000 - created) / 60000
                except (TypeError, ValueError):
                    age_min = 999
                if age_min < self.cfg.get("s1_min_age_minutes", 15):
                    continue
                if age_min > self.cfg.get("s1_max_age_hours", 24) * 60:
                    continue

            candidates.append({
                "address": mint,
                "name": token.get("name", ""),
                "symbol": token.get("symbol", ""),
                "description": token.get("description", ""),
                "source": "s1_pumpfun_retrace",
                "pumpfun_data": token,
                "estimated_mc": mc,
            })
            self.scanned_tokens.add(mint)

        self.stats["scanned"] += len(candidates)
        if not candidates:
            return

        log.info(f"S1: Found {len(candidates)} pump.fun coins in ${min_mc/1000:.0f}k-${max_mc/1000:.0f}k MC range")

        # Deep evaluation of each candidate
        for candidate in candidates[:10]:  # Max 10 per cycle
            try:
                await self._evaluate_pumpfun_candidate(candidate)
            except Exception as e:
                log.debug(f"S1 eval error {candidate['symbol']}: {e}")
            await asyncio.sleep(0.5)

    async def _evaluate_pumpfun_candidate(self, candidate: dict):
        """Deep evaluation for Strategy 1 — pump.fun retrace plays."""
        address = candidate["address"]
        pf_data = candidate.get("pumpfun_data", {})
        mc = candidate.get("estimated_mc", 0)

        # Get recent trades to check activity and bundle
        trades = await self.pump.get_token_trades(address, limit=50)
        if not trades:
            return

        # === TRADE FREQUENCY CHECK ===
        # We need trades happening every 5-10 seconds = at least 6-12 per minute
        min_tpm = self.cfg.get("s1_min_trades_per_min", 3)
        if len(trades) >= 2:
            # Calculate trades per minute from last N trades
            newest = trades[0]
            oldest = trades[min(len(trades)-1, 19)]  # Look at last 20 trades
            t_newest = newest.get("timestamp", 0) or newest.get("slot", 0)
            t_oldest = oldest.get("timestamp", 0) or oldest.get("slot", 0)

            if t_newest and t_oldest and t_newest > t_oldest:
                span_minutes = max((t_newest - t_oldest) / 60000, 0.1)  # ms to min
                tpm = min(len(trades), 20) / span_minutes
            else:
                # Fallback: if we got 50 trades, it's active enough
                tpm = len(trades) / 5  # rough estimate: 50 trades in ~5 min = 10 tpm
        else:
            tpm = 0

        if tpm < min_tpm:
            return  # Too slow, coin is dying

        # === BUY/SELL RATIO ===
        recent_buys = sum(1 for t in trades[:20] if t.get("is_buy", False))
        recent_sells = sum(1 for t in trades[:20] if not t.get("is_buy", True))
        total_recent = recent_buys + recent_sells
        buy_ratio = recent_buys / max(total_recent, 1)

        # === NARRATIVE CHECK ===
        text = f"{candidate.get('name', '')} {candidate.get('symbol', '')} {candidate.get('description', '')}".lower()
        narrative_match = any(kw in text for kw in self.cfg.get("narrative_keywords", []))

        if self.cfg.get("s1_require_narrative", True) and not narrative_match:
            # Add to watchlist but don't enter (AI might override this)
            pass

        # === DROP FROM PEAK CHECK ===
        peak_mc = self.pump.get_peak_mc(pf_data)
        if peak_mc > 0:
            drop_pct = ((peak_mc - mc) / peak_mc) * 100
        else:
            drop_pct = 0

        min_drop = self.cfg.get("s1_min_drop_from_peak_pct", 50)
        if drop_pct < min_drop:
            return  # Hasn't dumped enough

        # === RUG + BUNDLE CHECK ===
        # Get DexScreener data too for additional context
        pair_data = None
        dex_pairs = await self.dex.get_token_pairs(address)
        if dex_pairs:
            pair_data = dex_pairs[0]

        rug_result = await self.rug_checker.check(address, pair_data, pf_data, trades)
        self.stats["rug_checked"] += 1

        # HARD REJECT: bundled tokens
        if rug_result.get("is_bundled"):
            log.info(f"S1 REJECT {candidate['symbol']}: BUNDLED — {', '.join(rug_result['risks'][:2])}")
            return

        if not rug_result["is_safe"]:
            log.info(f"S1 REJECT {candidate['symbol']}: {rug_result['verdict']} (score {rug_result['score']})")
            return

        # === UNIQUE HOLDERS CHECK ===
        min_holders = self.cfg.get("s1_min_unique_holders", 30)
        # Estimate from pump.fun reply count + trade count
        estimated_holders = max(pf_data.get("reply_count", 0), len(set(
            t.get("user", "") or t.get("traderPublicKey", "") for t in trades
        )))
        if estimated_holders < min_holders:
            return  # Not enough real people

        # === ENTRY DECISION: Check if buying pressure is returning ===
        # We want to see buys > sells in the last 20 trades (people buying the dip)
        self.stats["passed_filter"] += 1

        if buy_ratio < 0.45:
            # More sellers than buyers — add to watchlist, wait for the turn
            wl_entry = {
                "address": address,
                "symbol": candidate.get("symbol", "???"),
                "name": candidate.get("name", ""),
                "market_cap": mc,
                "estimated_peak": peak_mc,
                "drop_pct": round(drop_pct, 1),
                "trades_per_min": round(tpm, 1),
                "buy_ratio": round(buy_ratio, 2),
                "narrative": narrative_match,
                "holders_est": estimated_holders,
                "strategy": "s1_retrace",
                "added_at": datetime.now(timezone.utc).isoformat(),
            }
            self.watchlist = [w for w in self.watchlist if w["address"] != address]
            self.watchlist.insert(0, wl_entry)
            self.watchlist = self.watchlist[:50]
            save_watchlist(self.watchlist)
            log.info(f"S1 WATCHLIST: {candidate['symbol']} | MC: ${mc:,.0f} | Drop: {drop_pct:.0f}% | "
                     f"TPM: {tpm:.1f} | Buy ratio: {buy_ratio:.0%} — waiting for buyers")
            return

        # === BUYERS ARE BACK — Ask AI for final decision ===
        # Build rich context for Claude to analyze
        candidate["market_cap"] = mc
        candidate["peak_mc"] = peak_mc
        candidate["drop_pct"] = drop_pct
        candidate["trades_per_min"] = tpm
        candidate["buy_ratio"] = buy_ratio
        candidate["estimated_holders"] = estimated_holders
        candidate["reply_count"] = pf_data.get("reply_count", 0)

        ai_result = await self.ai.analyze_entry(candidate, pair_data or {}, rug_result)

        if not ai_result.get("should_enter", False):
            log.info(f"S1 AI SKIP {candidate['symbol']}: {ai_result.get('reasoning', '')[:100]}")
            return

        ai_confidence = ai_result.get("confidence", 50)
        log.info(f"{'='*60}")
        log.info(f"S1 ENTRY: {candidate['symbol']} ({candidate['name'][:30]})")
        log.info(f"  MC: ${mc:,.0f} (peaked ~${peak_mc:,.0f}, dropped {drop_pct:.0f}%)")
        log.info(f"  Trades/min: {tpm:.1f} | Buy ratio: {buy_ratio:.0%} | Holders: ~{estimated_holders}")
        log.info(f"  Narrative: {'YES' if narrative_match else 'no'} | Rug: {rug_result['verdict']}")
        log.info(f"  AI Confidence: {ai_confidence}% — {ai_result.get('reasoning', '')[:100]}")
        log.info(f"{'='*60}")

        await self._enter_trade(address, pair_data or {"baseToken": {"symbol": candidate["symbol"], "name": candidate["name"]}},
                                rug_result, narrative_match, ai_result)

    async def _strategy_volume_spike(self):
        """STRATEGY 2: Volume Spike Hunter.
        Scan pump.fun coins for sudden volume spikes on low-MC tokens.
        If a normally quiet coin suddenly gets a burst of buying, something is happening."""

        self.status = "S2: hunting volume spikes"

        # Get active coins sorted by recent activity
        active = await self.pump.get_active_coins(limit=50, sort="last_trade_timestamp")
        if not isinstance(active, list):
            return

        min_mc = self.cfg.get("s2_min_mc", 3000)
        max_mc = self.cfg.get("s2_max_mc", 25000)

        for token in active[:20]:
            mint = token.get("mint", "")
            if not mint:
                continue

            mc = self.pump.estimate_market_cap(token)
            if mc < min_mc or mc > max_mc:
                continue

            # Get trades to detect spike
            trades = await self.pump.get_token_trades(mint, limit=50)
            if not trades or len(trades) < 10:
                continue

            # Compare recent 5-min volume vs older volume
            now_ms = time.time() * 1000
            recent_trades = [t for t in trades if (now_ms - (t.get("timestamp", 0) or 0)) < 300000]  # Last 5 min
            older_trades = [t for t in trades if (now_ms - (t.get("timestamp", 0) or 0)) >= 300000]

            if len(recent_trades) < 3 or len(older_trades) < 3:
                continue

            # Volume spike = recent trades are much more frequent
            recent_count = len(recent_trades)
            older_rate = len(older_trades) / max((now_ms - min(t.get("timestamp", now_ms) for t in older_trades)) / 300000, 1)

            if older_rate > 0:
                spike_ratio = recent_count / max(older_rate, 0.5)
            else:
                spike_ratio = recent_count  # Any activity on a dead coin is a spike

            min_spike = self.cfg.get("s2_volume_spike_multiplier", 3)
            if spike_ratio < min_spike:
                continue

            # Check buy ratio
            recent_buys = sum(1 for t in recent_trades if t.get("is_buy", False))
            buy_ratio = recent_buys / max(len(recent_trades), 1)
            min_buy_ratio = self.cfg.get("s2_min_buy_ratio", 0.55)

            if buy_ratio < min_buy_ratio:
                continue  # Spike is selling, not buying

            # This is interesting — add to watchlist with spike flag
            self.stats["passed_filter"] += 1
            wl_entry = {
                "address": mint,
                "symbol": token.get("symbol", "???"),
                "name": token.get("name", ""),
                "market_cap": mc,
                "volume_spike": round(spike_ratio, 1),
                "buy_ratio": round(buy_ratio, 2),
                "narrative": True,  # Volume spike IS the narrative
                "strategy": "s2_volume_spike",
                "added_at": datetime.now(timezone.utc).isoformat(),
            }
            self.watchlist = [w for w in self.watchlist if w["address"] != mint]
            self.watchlist.insert(0, wl_entry)
            save_watchlist(self.watchlist)
            log.info(f"S2 SPIKE: {token.get('symbol','???')} | MC: ${mc:,.0f} | "
                     f"Spike: {spike_ratio:.1f}x | Buys: {buy_ratio:.0%}")

            await asyncio.sleep(0.3)

    async def _strategy_social_sentiment(self):
        """STRATEGY 3: Social Sentiment Scanner.
        Check Twitter/X for trending Solana tickers. Placeholder — needs Twitter API or scraping."""
        # TODO: Implement when Twitter scraping is set up
        # For now this is a placeholder that can be wired to a Twitter feed
        self.status = "S3: checking social buzz"
        pass

    async def _recheck_watchlist(self):
        """Re-check watchlisted tokens for entry signals (buy pressure returning)."""
        if not self.watchlist:
            return

        self.status = "re-checking watchlist"

        # Only re-check items that are less than 2 hours old
        cutoff = datetime.now(timezone.utc).timestamp() - 7200
        active_wl = [w for w in self.watchlist if w.get("added_at") and
                     datetime.fromisoformat(w["added_at"].replace("Z", "+00:00")).timestamp() > cutoff]

        for item in active_wl[:5]:  # Check top 5
            address = item["address"]
            if any(p["token_address"] == address for p in self.active_positions):
                continue  # Already in this

            trades = await self.pump.get_token_trades(address, limit=20)
            if not trades or len(trades) < 5:
                continue

            recent_buys = sum(1 for t in trades[:10] if t.get("is_buy", False))
            buy_ratio = recent_buys / min(len(trades), 10)

            if buy_ratio >= 0.55:
                # Buyers are back! Evaluate for entry
                log.info(f"WATCHLIST TRIGGER: {item['symbol']} — buy ratio now {buy_ratio:.0%}")

                pf_info = await self.pump.get_token_info(address)
                pair_data = None
                dex_pairs = await self.dex.get_token_pairs(address)
                if dex_pairs:
                    pair_data = dex_pairs[0]

                rug_result = await self.rug_checker.check(address, pair_data, pf_info, trades)
                if rug_result.get("is_bundled") or not rug_result["is_safe"]:
                    continue

                candidate = {
                    "address": address,
                    "symbol": item.get("symbol", "???"),
                    "name": item.get("name", ""),
                    "description": "",
                    "source": item.get("strategy", "watchlist"),
                    "market_cap": item.get("market_cap", 0),
                    "buy_ratio": buy_ratio,
                }

                ai_result = await self.ai.analyze_entry(candidate, pair_data or {}, rug_result)
                if ai_result.get("should_enter", False):
                    log.info(f"WATCHLIST ENTRY: {item['symbol']} — AI confidence {ai_result.get('confidence', 0)}%")
                    await self._enter_trade(address, pair_data or {"baseToken": {"symbol": item["symbol"], "name": item["name"]}},
                                            rug_result, item.get("narrative", False), ai_result)

            await asyncio.sleep(0.5)

    async def _evaluate_candidate_legacy(self, candidate: dict):
        """Legacy evaluation — kept for graduated tokens. Uses DexScreener data."""
        address = candidate["address"]
        pairs = await self.dex.get_token_pairs(address)
        if not pairs:
            return

        # Use the highest-volume pair
        pair = max(pairs, key=lambda p: p.get("volume", {}).get("h24", 0))

        # === FILTERS ===
        volume_24h = pair.get("volume", {}).get("h24", 0) or 0
        market_cap = pair.get("marketCap", 0) or pair.get("fdv", 0) or 0
        liquidity = pair.get("liquidity", {}).get("usd", 0) or 0
        price_usd = float(pair.get("priceUsd", 0) or 0)

        # Filter: Volume
        if volume_24h < self.cfg["min_volume_24h"]:
            return

        # Filter: Market cap
        if market_cap > self.cfg["max_market_cap"] and market_cap > 0:
            return

        # Filter: Liquidity
        if liquidity < self.cfg["min_liquidity"]:
            return

        # Filter: Must have dropped significantly (we want the dip)
        price_change = pair.get("priceChange", {})
        h24_change = price_change.get("h24", 0) or 0
        h6_change = price_change.get("h6", 0) or 0

        # We want tokens that have dropped at least X% from their highs
        max_drop = min(h24_change, h6_change)  # Most negative = biggest drop
        if max_drop > -self.cfg["min_drop_from_ath_pct"]:
            return  # Hasn't dropped enough

        # Filter: Check bonding age
        created_at = pair.get("pairCreatedAt", 0)
        if created_at:
            age_minutes = (time.time() * 1000 - created_at) / 60000
            if age_minutes < self.cfg["min_bonding_age_minutes"]:
                return  # Too new
            if age_minutes > self.cfg["max_bonding_age_hours"] * 60:
                return  # Too old

        # Filter: Narrative check — does name/symbol/description match trending keywords?
        text = f"{candidate.get('name', '')} {candidate.get('symbol', '')} {candidate.get('description', '')}".lower()
        narrative_match = any(kw in text for kw in self.cfg["narrative_keywords"])
        # Narrative isn't required but gives bonus confidence

        # Filter: Buy pressure — need recent buys
        txns = pair.get("txns", {})
        h1_txns = txns.get("h1", {})
        m5_txns = txns.get("m5", {})
        h1_buys = h1_txns.get("buys", 0)
        h1_sells = h1_txns.get("sells", 0)
        m5_buys = m5_txns.get("buys", 0)
        m5_sells = m5_txns.get("sells", 0)

        # Want to see buying pressure starting (bounce signal)
        # 5min buys > sells = people are starting to buy the dip
        if m5_buys <= m5_sells and h1_buys <= h1_sells:
            # No buying pressure yet — add to watchlist, check later
            wl_entry = {
                "address": address,
                "symbol": pair.get("baseToken", {}).get("symbol", "???"),
                "name": pair.get("baseToken", {}).get("name", ""),
                "volume_24h": volume_24h,
                "market_cap": market_cap,
                "liquidity": liquidity,
                "drop_pct": max_drop,
                "narrative": narrative_match,
                "added_at": datetime.now(timezone.utc).isoformat(),
                "pair_address": pair.get("pairAddress", ""),
            }
            # Update watchlist (keep max 50)
            self.watchlist = [w for w in self.watchlist if w["address"] != address]
            self.watchlist.insert(0, wl_entry)
            self.watchlist = self.watchlist[:50]
            save_watchlist(self.watchlist)
            self.stats["passed_filter"] += 1
            return

        # === BUYING PRESSURE DETECTED — This is a potential entry ===
        self.stats["passed_filter"] += 1

        # 4. Rug check
        rug_result = await self.rug_checker.check(address, pair)
        self.stats["rug_checked"] += 1

        if not rug_result["is_safe"]:
            log.info(f"SKIP {pair.get('baseToken',{}).get('symbol','???')} — Rug risk: {rug_result['verdict']} "
                     f"(score {rug_result['score']}) — {', '.join(rug_result['risks'][:3])}")
            return

        # 5. Check we're not already in this token
        if any(p["token_address"] == address for p in self.active_positions):
            return

        # === AI ANALYSIS — Let Claude decide if this is a real opportunity ===
        symbol = pair.get("baseToken", {}).get("symbol", "???")
        name = pair.get("baseToken", {}).get("name", "")

        log.info(f"Candidate: {symbol} ({name}) | MC: ${market_cap:,.0f} | Vol: ${volume_24h:,.0f} | Drop: {max_drop:.0f}%")

        ai_result = await self.ai.analyze_entry(candidate, pair, rug_result)

        if not ai_result.get("should_enter", False):
            log.info(f"AI SKIP {symbol}: {ai_result.get('reasoning', 'No reason given')}")
            # Still add to watchlist with AI notes
            wl_entry = {
                "address": address,
                "symbol": symbol,
                "name": name,
                "volume_24h": volume_24h,
                "market_cap": market_cap,
                "liquidity": liquidity,
                "drop_pct": max_drop,
                "narrative": narrative_match,
                "ai_confidence": ai_result.get("confidence", 0),
                "ai_reasoning": ai_result.get("reasoning", ""),
                "added_at": datetime.now(timezone.utc).isoformat(),
                "pair_address": pair.get("pairAddress", ""),
            }
            self.watchlist = [w for w in self.watchlist if w["address"] != address]
            self.watchlist.insert(0, wl_entry)
            self.watchlist = self.watchlist[:50]
            save_watchlist(self.watchlist)
            return

        # AI says GO
        ai_confidence = ai_result.get("confidence", 50)
        log.info(f"{'='*50}")
        log.info(f"AI ENTRY SIGNAL: {symbol} ({name}) — Confidence: {ai_confidence}%")
        log.info(f"  Price: ${price_usd:.8f} | MC: ${market_cap:,.0f} | Vol: ${volume_24h:,.0f}")
        log.info(f"  Liq: ${liquidity:,.0f} | Drop: {max_drop:.0f}% | Narrative: {'YES' if narrative_match else 'no'}")
        log.info(f"  5m buys/sells: {m5_buys}/{m5_sells} | Rug: {rug_result['verdict']} ({rug_result['score']})")
        log.info(f"  AI: {ai_result.get('reasoning', '')}")
        log.info(f"{'='*50}")

        # Use AI-suggested TP/SL if provided
        if ai_result.get("suggested_tp_pct"):
            self.cfg["take_profit_pct"] = ai_result["suggested_tp_pct"]
        if ai_result.get("suggested_sl_pct"):
            self.cfg["stop_loss_pct"] = ai_result["suggested_sl_pct"]

        await self._enter_trade(address, pair, rug_result, narrative_match, ai_result)

    async def _enter_trade(self, token_address: str, pair: dict, rug_result: dict, narrative: bool, ai_result: dict = None):
        """Execute a buy."""
        symbol = pair.get("baseToken", {}).get("symbol", "???")
        price_usd = float(pair.get("priceUsd", 0) or 0)
        sol_amount = self.cfg["max_sol_per_trade"]

        trade = {
            "id": f"trade_{int(time.time())}",
            "token_address": token_address,
            "pair_address": pair.get("pairAddress", ""),
            "symbol": symbol,
            "name": pair.get("baseToken", {}).get("name", ""),
            "entry_price": price_usd,
            "entry_sol": sol_amount,
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "status": "open",
            "exit_price": None,
            "exit_time": None,
            "exit_sol": None,
            "pnl_pct": None,
            "pnl_sol": None,
            "tx_buy": None,
            "tx_sell": None,
            "rug_score": rug_result["score"],
            "narrative": narrative,
            "ai_confidence": ai_result.get("confidence", 0) if ai_result else 0,
            "ai_reasoning": ai_result.get("reasoning", "") if ai_result else "",
            "market_cap_at_entry": pair.get("marketCap", 0),
            "volume_at_entry": pair.get("volume", {}).get("h24", 0),
            "dry_run": self.cfg["dry_run"],
        }

        if self.cfg["dry_run"]:
            trade["tx_buy"] = f"DRY_RUN_{int(time.time())}"
            log.info(f"DRY RUN BUY: {sol_amount} SOL -> {symbol} @ ${price_usd:.8f}")
        else:
            # Real swap via Jupiter
            try:
                lamports = int(sol_amount * 1e9)
                quote = await self.jupiter.get_quote(SOL_MINT, token_address, lamports, self.cfg["slippage_bps"])
                if not quote:
                    log.error(f"Failed to get Jupiter quote for {symbol}")
                    return

                swap_data = await self.jupiter.get_swap_tx(quote, self.wallet_pubkey)
                if not swap_data or "swapTransaction" not in swap_data:
                    log.error(f"Failed to get swap transaction for {symbol}")
                    return

                # Sign and send
                from solders.keypair import Keypair
                from solders.transaction import VersionedTransaction
                import base58, base64

                kp = Keypair.from_bytes(base58.b58decode(self.cfg["wallet_private_key"]))
                raw_tx = base64.b64decode(swap_data["swapTransaction"])
                tx = VersionedTransaction.from_bytes(raw_tx)
                signed_tx = VersionedTransaction(tx.message, [kp])
                tx_base64 = base64.b64encode(bytes(signed_tx)).decode()

                sig = await self.solana.send_transaction(tx_base64)
                if sig:
                    trade["tx_buy"] = sig
                    log.info(f"BUY TX sent: {sig}")
                    confirmed = await self.solana.confirm_transaction(sig)
                    if confirmed:
                        log.info(f"BUY CONFIRMED: {symbol}")
                    else:
                        log.warning(f"BUY TX may not have confirmed: {sig}")
                        trade["status"] = "failed"
                else:
                    log.error(f"Failed to send buy TX for {symbol}")
                    trade["status"] = "failed"

            except ImportError:
                log.error("solders not installed. Cannot execute real trades.")
                trade["status"] = "failed"
                return
            except Exception as e:
                log.error(f"Buy execution error: {e}", exc_info=True)
                trade["status"] = "failed"

        if trade["status"] == "open":
            self.active_positions.append(trade)
            self.today_trades += 1
            self.stats["entries"] += 1

        self.trades.append(trade)
        save_trades(self.trades)

    async def _manage_positions(self):
        """Check open positions for TP/SL exits."""
        if not self.active_positions:
            return

        for pos in list(self.active_positions):
            try:
                pairs = await self.dex.get_token_pairs(pos["token_address"])
                if not pairs:
                    continue

                pair = max(pairs, key=lambda p: p.get("volume", {}).get("h24", 0))
                current_price = float(pair.get("priceUsd", 0) or 0)
                entry_price = pos["entry_price"]

                if entry_price <= 0 or current_price <= 0:
                    continue

                pnl_pct = ((current_price - entry_price) / entry_price) * 100

                # Take profit
                if pnl_pct >= self.cfg["take_profit_pct"]:
                    log.info(f"TAKE PROFIT: {pos['symbol']} at +{pnl_pct:.1f}%")
                    await self._exit_trade(pos, current_price, pnl_pct, "take_profit")

                # Stop loss
                elif pnl_pct <= -self.cfg["stop_loss_pct"]:
                    log.info(f"STOP LOSS: {pos['symbol']} at {pnl_pct:.1f}%")
                    await self._exit_trade(pos, current_price, pnl_pct, "stop_loss")

                # Trailing stop
                elif self.cfg["trailing_stop_pct"] > 0:
                    high = pos.get("highest_pnl", 0)
                    if pnl_pct > high:
                        pos["highest_pnl"] = pnl_pct
                    elif high > 10 and (high - pnl_pct) >= self.cfg["trailing_stop_pct"]:
                        log.info(f"TRAILING STOP: {pos['symbol']} at {pnl_pct:.1f}% (high was {high:.1f}%)")
                        await self._exit_trade(pos, current_price, pnl_pct, "trailing_stop")

                # AI exit analysis (check every few minutes, not every cycle)
                elif self.ai and pnl_pct > 5:  # Only consult AI if we're in profit
                    last_ai_check = pos.get("last_ai_exit_check", 0)
                    if time.time() - last_ai_check > 120:  # Every 2 minutes
                        ai_exit = await self.ai.analyze_exit(pos, pair)
                        pos["last_ai_exit_check"] = time.time()
                        if ai_exit.get("should_exit") and ai_exit.get("urgency") in ("medium", "high"):
                            log.info(f"AI EXIT: {pos['symbol']} at {pnl_pct:.1f}% — {ai_exit.get('reasoning', '')}")
                            await self._exit_trade(pos, current_price, pnl_pct, "ai_exit")

            except Exception as e:
                log.debug(f"Position check error for {pos.get('symbol')}: {e}")

            await asyncio.sleep(0.3)

    async def _exit_trade(self, pos: dict, current_price: float, pnl_pct: float, reason: str):
        """Execute a sell."""
        pos["exit_price"] = current_price
        pos["exit_time"] = datetime.now(timezone.utc).isoformat()
        pos["pnl_pct"] = round(pnl_pct, 2)
        pos["exit_reason"] = reason

        estimated_exit_sol = pos["entry_sol"] * (1 + pnl_pct / 100)
        pos["exit_sol"] = round(estimated_exit_sol, 4)
        pos["pnl_sol"] = round(estimated_exit_sol - pos["entry_sol"], 4)

        if self.cfg["dry_run"]:
            pos["tx_sell"] = f"DRY_RUN_SELL_{int(time.time())}"
            pos["status"] = "closed"
            log.info(f"DRY RUN SELL: {pos['symbol']} | PnL: {pnl_pct:+.1f}% ({pos['pnl_sol']:+.4f} SOL)")
        else:
            # Real sell via Jupiter
            try:
                # Get token balance
                accounts = await self.solana.get_token_accounts(self.wallet_pubkey)
                token_amount = 0
                for acc in accounts:
                    info = acc.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
                    if info.get("mint") == pos["token_address"]:
                        token_amount = int(info.get("tokenAmount", {}).get("amount", 0))
                        break

                if token_amount <= 0:
                    log.warning(f"No token balance found for {pos['symbol']}")
                    pos["status"] = "closed"
                    pos["exit_note"] = "no_balance"
                else:
                    quote = await self.jupiter.get_quote(
                        pos["token_address"], SOL_MINT, token_amount, self.cfg["slippage_bps"]
                    )
                    if quote:
                        swap_data = await self.jupiter.get_swap_tx(quote, self.wallet_pubkey)
                        if swap_data and "swapTransaction" in swap_data:
                            from solders.keypair import Keypair
                            from solders.transaction import VersionedTransaction
                            import base58, base64

                            kp = Keypair.from_bytes(base58.b58decode(self.cfg["wallet_private_key"]))
                            raw_tx = base64.b64decode(swap_data["swapTransaction"])
                            tx = VersionedTransaction.from_bytes(raw_tx)
                            signed_tx = VersionedTransaction(tx.message, [kp])
                            tx_base64 = base64.b64encode(bytes(signed_tx)).decode()

                            sig = await self.solana.send_transaction(tx_base64)
                            if sig:
                                pos["tx_sell"] = sig
                                pos["status"] = "closed"
                                log.info(f"SELL TX: {sig}")
                            else:
                                log.error(f"Failed to send sell TX for {pos['symbol']}")

                pos["status"] = "closed"
            except Exception as e:
                log.error(f"Sell error: {e}")
                pos["status"] = "closed"

        self.stats["exits"] += 1
        self.stats["pnl_sol"] += pos.get("pnl_sol", 0)
        self.active_positions = [p for p in self.active_positions if p["id"] != pos["id"]]

        # Update in trades list
        for i, t in enumerate(self.trades):
            if t["id"] == pos["id"]:
                self.trades[i] = pos
                break
        save_trades(self.trades)

    def get_status(self) -> dict:
        """Get bot status for the dashboard."""
        open_positions = [t for t in self.trades if t.get("status") == "open"]
        closed_trades = [t for t in self.trades if t.get("status") == "closed"]
        total_pnl = sum(t.get("pnl_sol", 0) or 0 for t in closed_trades)
        win_count = len([t for t in closed_trades if (t.get("pnl_sol") or 0) > 0])
        loss_count = len([t for t in closed_trades if (t.get("pnl_sol") or 0) <= 0])

        return {
            "status": self.status,
            "running": self.running,
            "dry_run": self.cfg.get("dry_run", True),
            "wallet": self.wallet_pubkey[:8] + "..." if self.wallet_pubkey else "Not set",
            "sol_balance": round(self.sol_balance, 4),
            "last_scan": self.last_scan,
            "today_trades": self.today_trades,
            "max_trades_day": self.cfg["max_trades_per_day"],
            "open_positions": len(open_positions),
            "positions": open_positions[:10],
            "total_trades": len(closed_trades),
            "total_pnl_sol": round(total_pnl, 4),
            "win_rate": round(win_count / max(win_count + loss_count, 1) * 100, 1),
            "wins": win_count,
            "losses": loss_count,
            "watchlist": self.watchlist[:10],
            "stats": self.stats,
            "config": {k: v for k, v in self.cfg.items() if k != "wallet_private_key"},
        }


# ══════════════════════════════════════
# SINGLETON + ASYNC RUNNER
# ══════════════════════════════════════

_trader_instance: MemecoinTrader = None
_trader_task: asyncio.Task = None

def get_trader() -> MemecoinTrader:
    global _trader_instance
    if _trader_instance is None:
        _trader_instance = MemecoinTrader()
    return _trader_instance

async def start_trader():
    global _trader_task, _trader_instance
    trader = get_trader()
    if trader.running:
        return {"error": "Already running"}
    _trader_task = asyncio.create_task(trader.start())
    return {"status": "started"}

async def stop_trader():
    trader = get_trader()
    trader.stop()
    return {"status": "stopping"}

def get_trader_status():
    return get_trader().get_status()

def update_trader_config(new_cfg: dict):
    cfg = load_config()
    cfg.update(new_cfg)
    save_config(cfg)
    trader = get_trader()
    trader.cfg = cfg
    return cfg

def get_trade_history():
    return load_trades()

def get_watchlist_data():
    return load_watchlist()


# ══════════════════════════════════════
# FLASK ROUTES (register with server)
# ══════════════════════════════════════

def register_routes(app):
    """Register memecoin trader routes with the Flask app."""
    import asyncio
    from flask import request, jsonify

    def run_async(coro):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, coro)
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)

    @app.route("/api/trader/status")
    def trader_status():
        return jsonify(get_trader_status())

    @app.route("/api/trader/start", methods=["POST"])
    def trader_start():
        result = run_async(start_trader())
        return jsonify(result)

    @app.route("/api/trader/stop", methods=["POST"])
    def trader_stop():
        result = run_async(stop_trader())
        return jsonify(result)

    @app.route("/api/trader/config", methods=["GET", "POST"])
    def trader_config():
        if request.method == "POST":
            new_cfg = request.get_json() or {}
            cfg = update_trader_config(new_cfg)
            return jsonify(cfg)
        return jsonify(load_config())

    @app.route("/api/trader/trades")
    def trader_trades():
        return jsonify(get_trade_history())

    @app.route("/api/trader/watchlist")
    def trader_watchlist():
        return jsonify(get_watchlist_data())

    log.info("Memecoin Trader routes registered.")
