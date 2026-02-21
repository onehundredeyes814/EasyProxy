import asyncio
import logging
import time
import socket
import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from aiohttp_socks import ProxyConnector
from typing import Optional, Dict, Any
import random

logger = logging.getLogger(__name__)

class ExtractorError(Exception):
    pass

class VavooExtractor:
    """Vavoo URL extractor per risolvere link vavoo.to"""
    
    def __init__(self, request_headers: dict, proxies: list = None):
        self.request_headers = request_headers
        self.base_headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.session = None
        self.mediaflow_endpoint = "proxy_stream_endpoint"
        self.proxies = proxies or []

    def _get_random_proxy(self):
        """Restituisce un proxy casuale dalla lista."""
        return random.choice(self.proxies) if self.proxies else None
        
    async def _get_session(self):
        if self.session is None or self.session.closed:
            timeout = ClientTimeout(total=60, connect=30, sock_read=30)
            proxy = self._get_random_proxy()
            if proxy:
                logger.info(f"Using proxy {proxy} for Vavoo session.")
                connector = ProxyConnector.from_url(proxy)
            else:
                connector = TCPConnector(
                    limit=0,
                    limit_per_host=0,
                    keepalive_timeout=60,
                    enable_cleanup_closed=True,
                    force_close=False,
                    use_dns_cache=True,
                    family=socket.AF_INET # Force IPv4
                )

            self.session = ClientSession(
                timeout=timeout,
                connector=connector,
                headers={'User-Agent': self.base_headers["user-agent"]}
            )
        return self.session

    async def get_auth_signature(self, retries=3, delay=2) -> Optional[str]:
        """Ottiene la signature di autenticazione per l'API Vavoo con retry logic"""
        headers = {
            "user-agent": "okhttp/4.11.0",
            "accept": "application/json", 
            "content-type": "application/json; charset=utf-8",
            "accept-encoding": "gzip"
        }
        current_time = int(time.time() * 1000)
        
        data = {
            "token": "tosFwQCJMS8qrW_AjLoHPQ41646J5dRNha6ZWHnijoYQQQoADQoXYSo7ki7O5-CsgN4CH0uRk6EEoJ0728ar9scCRQW3ZkbfrPfeCXW2VgopSW2FWDqPOoVYIuVPAOnXCZ5g",
            "reason": "app-blur",
            "locale": "de",
            "theme": "dark",
            "metadata": {
                "device": {
                    "type": "Handset",
                    "brand": "google",
                    "model": "Nexus",
                    "name": "21081111RG",
                    "uniqueId": "d10e5d99ab665233"
                },
                "os": {
                    "name": "android",
                    "version": "7.1.2",
                    "abis": ["arm64-v8a", "armeabi-v7a", "armeabi"],
                    "host": "android"
                },
                "app": {
                    "platform": "android",
                    "version": "3.1.20",
                    "buildId": "289515000",
                    "engine": "hbc85",
                    "signatures": ["6e8a975e3cbf07d5de823a760d4c2547f86c1403105020adee5de67ac510999e"],
                    "installer": "app.revanced.manager.flutter"
                },
                "version": {
                    "package": "tv.vavoo.app",
                    "binary": "3.1.20",
                    "js": "3.1.20"
                }
            },
            "appFocusTime": 0,
            "playerActive": False,
            "playDuration": 0,
            "devMode": False,
            "hasAddon": True,
            "castConnected": False,
            "package": "tv.vavoo.app",
            "version": "3.1.20",
            "process": "app",
            "firstAppStart": 1743962904623,
            "lastAppStart": 1743962904623,
            "ipLocation": "",
            "adblockEnabled": True,
            "proxy": {
                "supported": ["ss", "openvpn"],
                "engine": "ss",
                "ssVersion": 1,
                "enabled": True,
                "autoServer": True,
                "id": "pl-waw"
            },
            "iap": {
                "supported": False
            }
        }
        
        for attempt in range(retries):
            try:
                session = await self._get_session()
                
                async with session.post(
                    "https://www.vavoo.tv/api/app/ping",
                    json=data,
                    headers=headers
                ) as resp:
                    resp.raise_for_status()
                    result = await resp.json()
                    logger.info(f"Vavoo ping response: {result}")
                    addon_sig = result.get("addonSig")
                    
                    if addon_sig:
                        logger.info(f"Vavoo signature obtained successfully (attempt {attempt + 1})")
                        return addon_sig
                    else:
                        logger.warning(f"No addonSig in Vavoo API response (attempt {attempt + 1})")
                        
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for Vavoo signature: {str(e)}")
                if attempt < retries - 1:
                    await asyncio.sleep(delay * (attempt + 1))
                    if self.session and not self.session.closed:
                        await self.session.close()
                    self.session = None
                else:
                    logger.error(f"All attempts failed for Vavoo signature: {str(e)}")
                    return None
        
        return None

    async def get_guest_signature(self, retries=3, delay=2) -> Optional[str]:
        """Ottiene la signature guest per l'API Vavoo (ping2) con retry logic"""
        vec = {
            "vec": "9frjpxPjxSNilxJPCJ0XGYs6scej3dW/h/VWlnKUiLSG8IP7mfyDU7NirOlld+VtCKGj03XjetfliDMhIev7wcARo+YTU8KPFuVQP9E2DVXzY2BFo1NhE6qEmPfNDnm74eyl/7iFJ0EETm6XbYyz8IKBkAqPN/Spp3PZ2ulKg3QBSDxcVN4R5zRn7OsgLJ2CNTuWkd/h451lDCp+TtTuvnAEhcQckdsydFhTZCK5IiWrrTIC/d4qDXEd+GtOP4hPdoIuCaNzYfX3lLCwFENC6RZoTBYLrcKVVgbqyQZ7DnLqfLqvf3z0FVUWx9H21liGFpByzdnoxyFkue3NzrFtkRL37xkx9ITucepSYKzUVEfyBh+/3mtzKY26VIRkJFkpf8KVcCRNrTRQn47Wuq4gC7sSwT7eHCAydKSACcUMMdpPSvbvfOmIqeBNA83osX8FPFYUMZsjvYNEE3arbFiGsQlggBKgg1V3oN+5ni3Vjc5InHg/xv476LHDFnNdAJx448ph3DoAiJjr2g4ZTNynfSxdzA68qSuJY8UjyzgDjG0RIMv2h7DlQNjkAXv4k1BrPpfOiOqH67yIarNmkPIwrIV+W9TTV/yRyE1LEgOr4DK8uW2AUtHOPA2gn6P5sgFyi68w55MZBPepddfYTQ+E1N6R/hWnMYPt/i0xSUeMPekX47iucfpFBEv9Uh9zdGiEB+0P3LVMP+q+pbBU4o1NkKyY1V8wH1Wilr0a+q87kEnQ1LWYMMBhaP9yFseGSbYwdeLsX9uR1uPaN+u4woO2g8sw9Y5ze5XMgOVpFCZaut02I5k0U4WPyN5adQjG8sAzxsI3KsV04DEVymj224iqg2Lzz53Xz9yEy+7/85ILQpJ6llCyqpHLFyHq/kJxYPhDUF755WaHJEaFRPxUqbparNX+mCE9Xzy7Q/KTgAPiRS41FHXXv+7XSPp4cy9jli0BVnYf13Xsp28OGs/D8Nl3NgEn3/eUcMN80JRdsOrV62fnBVMBNf36+LbISdvsFAFr0xyuPGmlIETcFyxJkrGZnhHAxwzsvZ+Uwf8lffBfZFPRrNv+tgeeLpatVcHLHZGeTgWWml6tIHwWUqv2TVJeMkAEL5PPS4Gtbscau5HM+FEjtGS+KClfX1CNKvgYJl7mLDEf5ZYQv5kHaoQ6RcPaR6vUNn02zpq5/X3EPIgUKF0r/0ctmoT84B2J1BKfCbctdFY9br7JSJ6DvUxyde68jB+Il6qNcQwTFj4cNErk4x719Y42NoAnnQYC2/qfL/gAhJl8TKMvBt3Bno+va8ve8E0z8yEuMLUqe8OXLce6nCa+L5LYK1aBdb60BYbMeWk1qmG6Nk9OnYLhzDyrd9iHDd7X95OM6X5wiMVZRn5ebw4askTTc50xmrg4eic2U1w1JpSEjdH/u/hXrWKSMWAxaj34uQnMuWxPZEXoVxzGyuUbroXRfkhzpqmqqqOcypjsWPdq5BOUGL/Riwjm6yMI0x9kbO8+VoQ6RYfjAbxNriZ1cQ+AW1fqEgnRWXmjt4Z1M0ygUBi8w71bDML1YG6UHeC2cJ2CCCxSrfycKQhpSdI1QIuwd2eyIpd4LgwrMiY3xNWreAF+qobNxvE7ypKTISNrz0iYIhU0aKNlcGwYd0FXIRfKVBzSBe4MRK2pGLDNO6ytoHxvJweZ8h1XG8RWc4aB5gTnB7Tjiqym4b64lRdj1DPHJnzD4aqRixpXhzYzWVDN2kONCR5i2quYbnVFN4sSfLiKeOwKX4JdmzpYixNZXjLkG14seS6KR0Wl8Itp5IMIWFpnNokjRH76RYRZAcx0jP0V5/GfNNTi5QsEU98en0SiXHQGXnROiHpRUDXTl8FmJORjwXc0AjrEMuQ2FDJDmAIlKUSLhjbIiKw3iaqp5TVyXuz0ZMYBhnqhcwqULqtFSuIKpaW8FgF8QJfP2frADf4kKZG1bQ99MrRrb2A="
        }
        
        for attempt in range(retries):
            try:
                session = await self._get_session()
                
                async with session.post(
                    "https://www.vavoo.tv/api/box/ping2",
                    data=vec
                ) as resp:
                    resp.raise_for_status()
                    result = await resp.json()
                    signed = result.get("response", {}).get("signed")
                    
                    if signed:
                        logger.info(f"Vavoo guest signature obtained successfully (attempt {attempt + 1})")
                        return signed
                    else:
                        logger.warning(f"No signed in Vavoo API response (attempt {attempt + 1})")
                        
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for Vavoo guest signature: {str(e)}")
                if attempt < retries - 1:
                    await asyncio.sleep(delay * (attempt + 1))
                    if self.session and not self.session.closed:
                        await self.session.close()
                    self.session = None
                else:
                    logger.error(f"All attempts failed for Vavoo guest signature: {str(e)}")
                    return None
        
        return None

    async def _resolve_vavoo_link(self, link: str, signature: str) -> Optional[str]:
        headers = {
            "user-agent": "MediaHubMX/2",
            "accept": "application/json",
            "content-type": "application/json; charset=utf-8", 
            "accept-encoding": "gzip",
            "mediahubmx-signature": signature
        }
        data = {
            "language": "de",
            "region": "AT",
            "url": link,
            "clientVersion": "3.0.2"
        }
        
        try:
            logger.info(f"Attempting to resolve Vavoo URL: {link}")
            session = await self._get_session()
            
            async with session.post(
                "https://vavoo.to/mediahubmx-resolve.json",
                json=data,
                headers=headers
            ) as resp:
                resp.raise_for_status()
                result = await resp.json()
                
                if isinstance(result, list) and result and result[0].get("url"):
                    resolved_url = result[0]["url"]
                    logger.info(f"Vavoo URL resolved successfully: {resolved_url}")
                    return resolved_url
                elif isinstance(result, dict) and result.get("url"):
                    resolved_url = result["url"]
                    logger.info(f"Vavoo URL resolved successfully: {resolved_url}")
                    return resolved_url
                else:
                    logger.warning(f"No URL found in Vavoo API response: {result}")
                    return None
        except Exception as e:
            logger.exception(f"Vavoo resolution failed for URL {link}: {str(e)}")
            return None

    async def extract(self, url: str, **kwargs) -> Dict[str, Any]:
        if "vavoo.to" not in url:
            raise ExtractorError("Not a valid Vavoo URL")

        # Use Direct Mode (ping2 + manual URL construction) as primary method
        # This matches the plugin's default behavior and bypasses the "promo" stream from resolve endpoint
        
        # However, for vavoo-iptv/play URLs, they seem to be direct and self-sufficient.
        # User reported the original URL works without proxy.
        # Plugin's Direct Mode (replacing with live2 + slicing) fails with 404/500 for this ID.
        # Appending vavoo_auth also fails with 404.
        # So we simply use the original URL, but ensure correct User-Agent.
        
        # guest_signature = await self.get_guest_signature()
        # if not guest_signature:
        #      raise ExtractorError("Failed to obtain Vavoo guest signature")

        resolved_url = url
        logger.info(f"Using Direct Mode (original URL): {resolved_url}")

        # Plugin uses VAVOO/2.6 for the stream request in Direct Mode
        stream_headers = {
            "user-agent": "VAVOO/2.6",
            "referer": "https://vavoo.to/",
        }

        return {
            "destination_url": resolved_url,
            "request_headers": stream_headers,
            "mediaflow_endpoint": self.mediaflow_endpoint,
        }

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
