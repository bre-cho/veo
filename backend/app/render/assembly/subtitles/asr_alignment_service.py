from __future__ import annotations

from typing import List


class ASRAlignmentService:
    """Aligns a transcript to an audio file to produce word-level timestamps.

    Production implementations should delegate to a real forced-alignment
    engine such as WhisperX, Gentle, MFA, or provider speech-mark APIs.
    This stub distributes words evenly across the probed audio duration as
    a safe fallback when no real aligner is available.
    """

    def align(self, audio_path: str, transcript: str) -> List[dict]:
        """Return a list of word-timing dicts for the given audio and transcript.

        Args:
            audio_path: Absolute path to the audio file.
            transcript: The voiceover text to align.

        Returns:
            List of dicts with keys ``word``, ``start_sec``, ``end_sec``.
            Returns an empty list if the transcript contains no words.
        """
        words = transcript.split()
        if not words:
            return []

        duration_sec = self._probe_audio_duration(audio_path)
        per_word = duration_sec / len(words)

        return [
            {
                "word": word,
                "start_sec": round(idx * per_word, 2),
                "end_sec": round((idx + 1) * per_word, 2),
            }
            for idx, word in enumerate(words)
        ]

    def _probe_audio_duration(self, audio_path: str) -> float:
        """Return the duration of the audio file in seconds.

        The stub always returns 6.0 s.  Replace with an ffprobe / mutagen
        call in production.
        """
        return 6.0
