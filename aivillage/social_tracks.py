"""Independent speech lanes for simultaneous village conversations."""
from .voice.tts import VoiceService


class SocialTracksMixin:
    def _conversation_members(self, speaker):
        members = [speaker]
        current = speaker
        while len(members) < 4:
            current = self.agent_by_key.get(current.partner or "")
            if current is None or current.state != "talk" or current in members:
                break
            members.append(current)
        return members

    def _social_track_count(self):
        return int(bool(self.script) or self.voice.is_busy()) + len(self._social_tracks)

    def _add_social_script(self, script):
        if not self.script and not self.voice.is_busy():
            self.script.extend(script)
            return
        voice = VoiceService(self.config, self.i18n, self.voice.profiles)
        voice.muted = self.voice.muted
        voice.speak_ambient = self.voice.speak_ambient
        self._social_tracks.append((script, voice))

    def _sync_track_voice(self, voice):
        voice.enabled = self.voice.enabled
        voice.speak_ambient = self.voice.speak_ambient
        voice.volume = self.voice.volume
        voice.rate_scale = self.voice.rate_scale
        if voice.muted != self.voice.muted:
            voice.toggle_mute()

    def _close_social_tracks(self):
        for script, voice in self._social_tracks:
            script.clear()
            voice.shutdown()
        self._social_tracks.clear()

    def _tick_social_tracks(self):
        self._tick_one_script(self.script, self.voice)
        for script, voice in self._social_tracks[:]:
            self._sync_track_voice(voice)
            self._tick_one_script(script, voice)
            if not script and not voice.is_busy():
                if voice.status.startswith(("voice error", "voice unavailable", "voice playback stalled")):
                    self.voice.ok = False
                    self.voice.status = voice.status
                voice.shutdown()
                self._social_tracks.remove((script, voice))
