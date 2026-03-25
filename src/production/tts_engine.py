import os
import time
import asyncio
from loguru import logger
from dotenv import load_dotenv
from src.intelligence.config import TenantConfig, system_config

load_dotenv()

class TTSEngine:
    """
    Mengubah script teks menjadi audio MP3.
    Primary: Edge TTS (Microsoft) — gratis, tidak butuh API key.
    Fallback: ElevenLabs — butuh paid plan.
    Multi-tenant ready.
    """

    VOICES = {
        "universe_mysteries": {
            "edge_voice": "en-US-GuyNeural",
            "description": "Deep, authoritative — cocok untuk misteri & sains"
        },
        "fun_facts": {
            "edge_voice": "en-US-JennyNeural",
            "description": "Energetic, upbeat — cocok untuk fun facts"
        },
        "dark_history": {
            "edge_voice": "en-US-ChristopherNeural",
            "description": "Dramatic, intense — cocok untuk dark history"
        },
        "ocean_mysteries": {
            "edge_voice": "en-US-GuyNeural",
            "description": "Deep, mysterious — cocok untuk ocean content"
        },
    }

    def __init__(self):
        pass

    def _get_voice(self, niche: str) -> dict:
        return self.VOICES.get(niche, self.VOICES["universe_mysteries"])

    async def _generate_edge_tts(self, text: str, voice: str, output_path: str) -> bool:
        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, voice, rate="+10%", volume="+0%")
            await communicate.save(output_path)
            return True
        except Exception as e:
            logger.error(f"Edge TTS error: {e}")
            return False

    def generate(self, script: dict, tenant_config: TenantConfig, output_dir: str = "logs") -> str:
        full_script = script.get("full_script", "")
        if not full_script:
            parts = [
                script.get("hook", ""),
                script.get("build_up", ""),
                script.get("core_facts", ""),
                script.get("climax", ""),
                script.get("cta", "")
            ]
            full_script = " ".join(p for p in parts if p).strip()

        word_count = len(full_script.split())
        logger.info(f"Generating TTS: {word_count} words")

        voice_data = self._get_voice(tenant_config.niche)
        voice = voice_data["edge_voice"]
        logger.info(f"Voice: {voice} ({voice_data['description']})")

        os.makedirs(output_dir, exist_ok=True)
        timestamp = int(time.time())
        output_path = os.path.join(output_dir, f"audio_{tenant_config.tenant_id}_{timestamp}.mp3")

        success = asyncio.run(self._generate_edge_tts(full_script, voice, output_path))

        if success and os.path.exists(output_path):
            size_kb = os.path.getsize(output_path) / 1024
            logger.info(f"Audio generated: {output_path} ({size_kb:.1f} KB)")
            return output_path

        logger.error("TTS generation failed")
        return ""

    def get_duration(self, audio_path: str) -> float:
        try:
            size_bytes = os.path.getsize(audio_path)
            duration = (size_bytes * 8) / (128 * 1000)
            return round(duration, 1)
        except Exception:
            return 0.0


if __name__ == "__main__":
    from src.intelligence.trend_radar import TrendRadar
    from src.intelligence.niche_selector import NicheSelector
    from src.intelligence.script_engine import ScriptEngine
    from src.intelligence.hook_optimizer import HookOptimizer

    tenant = TenantConfig(tenant_id="ryan_andrian", niche="universe_mysteries")

    logger.info("Step 1-4: Running intelligence pipeline...")
    signals = TrendRadar().scan(tenant)
    topics = NicheSelector().select(signals, tenant)
    scripts = ScriptEngine().generate_batch(topics, tenant, count=1)
    optimized = HookOptimizer().optimize_batch(scripts, tenant)

    if not optimized:
        logger.error("No script available")
        exit(1)

    script = optimized[0]
    logger.info(f"Script: {script.get('title', '')}")
    logger.info(f"Hook  : {script.get('hook', '')}")

    logger.info("Step 5: Generating TTS audio...")
    tts = TTSEngine()
    audio_path = tts.generate(script, tenant)

    if audio_path:
        duration = tts.get_duration(audio_path)
        print(f"\n{'='*60}")
        print(f"TTS GENERATION COMPLETE")
        print(f"{'='*60}")
        print(f"Title   : {script.get('title', '')}")
        print(f"Hook    : {script.get('hook', '')}")
        print(f"Audio   : {audio_path}")
        print(f"Duration: ~{duration}s")
        print(f"Size    : {os.path.getsize(audio_path)/1024:.1f} KB")
        print(f"Voice   : {TTSEngine.VOICES[tenant.niche]['edge_voice']}")
        print(f"{'='*60}")
    else:
        print("TTS generation failed")
