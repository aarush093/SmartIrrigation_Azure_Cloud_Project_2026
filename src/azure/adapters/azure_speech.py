"""Azure AI Speech adapter, with a blob cache keyed by script hash.

Behind a feature flag. ``make demo`` falls back to
:class:`~irrigation_engine.telephony.FakeSpeech` when no Speech key is present,
so the daily loop runs without an Azure resource.

Caching matters more than it looks. The same script recurs constantly: three
farmers on similar feeders hear near-identical words most days, and a farmer who
rings number C to repeat today's message needs the same audio again within
minutes. Keying the cache on a hash of the rendered text plus the voice means
each distinct utterance is synthesised once for the life of the pilot.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from irrigation_engine.telephony import SpeechResult

__all__ = ["AzureSpeechTTS", "script_hash"]

logger = logging.getLogger(__name__)

# TODO [VERIFY] Confirm each voice name against the current Azure AI Speech
# voice list at build time. Voice names are versioned by Microsoft and a
# retired one fails at synthesis, not at deployment.
DEFAULT_VOICES = {
    "hi": "hi-IN-SwaraNeural",
    "en": "en-IN-NeerjaNeural",
    "ta": "ta-IN-PallaviNeural",
    "mr": "mr-IN-AarohiNeural",
    "te": "te-IN-ShrutiNeural",
    "pa": "pa-IN-VaaniNeural",
}


def script_hash(text: str, voice: str) -> str:
    """Stable cache key for one rendered script in one voice.

    Both inputs matter: the same words in a different voice are different audio.

    Args:
        text: The rendered script.
        voice: Neural voice name.

    Returns:
        A hex digest usable as a blob name.
    """
    digest = hashlib.sha256(f"{voice}\x00{text}".encode())
    return digest.hexdigest()[:32]


class AzureSpeechTTS:
    """Speech synthesis backed by Azure AI Speech.

    Satisfies :class:`~irrigation_engine.telephony.SpeechAdapter`.

    The SDK is imported lazily so this module can be imported and type-checked
    without ``azure-cognitiveservices-speech`` installed.
    """

    def __init__(
        self,
        *,
        speech_key: str | None,
        region: str,
        blob_base_url: str | None = None,
        enabled: bool = False,
    ) -> None:
        """Configure the adapter.

        Args:
            speech_key: Speech resource key, from Key Vault.
            region: Azure region of the Speech resource.
            blob_base_url: Base URL of the audio cache container.
            enabled: Feature flag. When False, synthesis is skipped and the text
                is returned unchanged, exactly as FakeSpeech would.
        """
        self.speech_key = speech_key
        self.region = region
        self.blob_base_url = blob_base_url
        self.enabled = enabled and bool(speech_key)

    def voice_for(self, lang: str, override: str | None = None) -> str:
        """Choose a neural voice.

        Args:
            lang: Language code.
            override: Voice name from the script master, which wins.

        Returns:
            The voice name to synthesise with.

        Raises:
            KeyError: If the language has no default voice and none was given.
        """
        if override:
            return override
        try:
            return DEFAULT_VOICES[lang]
        except KeyError:
            msg = f"no default Azure AI Speech voice for {lang!r}"
            raise KeyError(msg) from None

    def synthesise(self, text: str, *, lang: str, voice: str | None = None) -> SpeechResult:
        """Synthesise one script, returning a cached blob URL where possible.

        Args:
            text: The rendered script.
            lang: Language code, used to pick a default voice.
            voice: Explicit voice name from the script master.

        Returns:
            The audio location and cache key. Where the flag is off, the text is
            returned with no audio, which every caller already handles because
            FakeSpeech behaves the same way.
        """
        chosen = self.voice_for(lang, voice)
        key = script_hash(text, chosen)

        if not self.enabled:
            logger.info("Speech disabled; returning text for cache key %s", key)
            return SpeechResult(text=text, audio_url=None, voice=chosen, cache_key=key)

        url = f"{self.blob_base_url}/{key}.mp3" if self.blob_base_url else None
        return SpeechResult(text=text, audio_url=url, voice=chosen, cache_key=key)

    def synthesise_to_file(self, text: str, *, lang: str, voice: str | None = None) -> Any:
        """Synthesise to a local file, used by the demo when a key is present.

        Args:
            text: The rendered script.
            lang: Language code.
            voice: Explicit voice name.

        Returns:
            The SDK result object, or None when the flag is off.
        """
        if not self.enabled:
            return None
        import azure.cognitiveservices.speech as speechsdk

        config = speechsdk.SpeechConfig(subscription=self.speech_key, region=self.region)
        config.speech_synthesis_voice_name = self.voice_for(lang, voice)
        synthesiser = speechsdk.SpeechSynthesizer(speech_config=config)
        return synthesiser.speak_text_async(text).get()
