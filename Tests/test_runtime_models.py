"""Executable design/reference models, NOT execution of C# or Unity/Udon APIs.

The companion AST checks constrain the C# implementation to these contracts.
Real client timing, VRChat transport, SDK binding and sound remain unverified here.
"""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import math
import random
import unittest


def wrap(hour):
    return hour % 24.0


def jst(network_utc):
    return wrap(network_utc.hour + 9 + network_utc.minute / 60
                + network_utc.second / 3600 + network_utc.microsecond / 3_600_000_000)


def server_delta(now, then):
    # Reference model of signed 32-bit millisecond server-clock wrap handling.
    # Production delegates this to the SDK's CalculateServerDeltaTime API.
    period = (2 ** 32) / 1000.0
    return ((now - then + period / 2) % period) - period / 2


@dataclass
class ClockModel:
    clock_initialized: bool = True
    mode: int = 0
    manual_hour: float = 18.5
    speed: float = 1.0
    anchor_hour: float = 0.0
    anchor_server: float = 0.0

    def hour(self, now, utc):
        if self.mode == 1:
            return jst(utc)
        if self.mode == 2:
            return wrap(self.anchor_hour + max(0, server_delta(now, self.anchor_server)) * self.speed / 3600)
        return wrap(self.manual_hour)

    def auto(self):
        self.mode, self.speed = 1, 1

    def manual(self, hour):
        self.manual_hour, self.mode, self.speed = wrap(hour), 0, 1

    def cycle(self, now, utc):
        previous = self.speed if self.mode == 2 else 1
        speed = next((v for v in (2, 5, 10, 30, 60) if previous < v), 1)
        if speed == 1:
            self.auto()
        else:
            self.anchor_hour = self.hour(now, utc) if self.mode == 2 else jst(utc)
            self.anchor_server, self.mode, self.speed = now, 2, speed

    def rebase(self, now, utc):
        if self.mode == 2 and server_delta(now, self.anchor_server) >= 600:
            self.anchor_hour = self.hour(now, utc)
            self.anchor_server = now


@dataclass
class SerializationModel:
    dirty: bool = False
    queued: bool = False
    next_send: float = 0
    requests: int = 0

    def edit(self):
        self.dirty = True

    def flush(self, now, owner=True, settled=True):
        if self.dirty and not self.queued and now >= self.next_send and owner and settled:
            self.queued = True
            self.next_send = now + .25
            self.requests += 1

    def pre(self):
        self.dirty = False

    def post(self, now, success=True, owner=True):
        self.queued = False
        if not success and owner:
            self.dirty = True
            self.next_send = now + 2

    def transfer(self, local_owner):
        self.queued = False
        self.dirty = local_owner

    def disable(self):
        self.queued = False

    def enable(self, owner):
        self.queued = False
        if owner:
            self.dirty = True


class BgmModel:
    """Same branch order and failed-clip quarantine as the runtime source."""
    def __init__(self, lengths, source=True):
        self.lengths = lengths
        self.source = source
        self.on = False
        self.failed = set()
        self.current = -1
        self.retry_at = 0
        self.saw_playback = False
        self.attempted = 0
        self.end = 0
        self.all_failed = False
        self.starts = []

    def valid(self):
        return [i for i, length in enumerate(self.lengths) if length is not None and length > .1]

    def candidates(self):
        choices = [i for i in self.valid() if i not in self.failed]
        return [i for i in choices if i != self.current] if len(choices) > 1 else choices

    def play(self, now, rng=None):
        if not self.source or not self.valid():
            self.current = -1
            return
        choices = self.candidates()
        if not choices:
            self.all_failed = True
            return
        self.current = (rng or random).choice(choices)
        self.saw_playback = False
        self.retry_at = 0
        self.attempted = now
        self.end = now + self.lengths[self.current]
        self.starts.append((now, self.current))

    def enable(self, now):
        self.on = True
        self.failed.clear()
        self.all_failed = False
        self.retry_at = 0
        self.play(now)

    def tick(self, now, playing=False):
        if self.on and self.source and playing:
            self.saw_playback = True
            if self.retry_at > 0:
                self.retry_at = 0
                self.failed.discard(self.current)
        if not self.on or not self.source or not self.valid() or self.all_failed:
            return
        if self.retry_at > 0:
            if now < self.retry_at:
                return
            self.retry_at = 0
            self.play(now)
            return
        if playing:
            self.saw_playback = True
            return
        if now < self.attempted + 3:
            return
        if not self.saw_playback or now + 1 < self.end:
            self.failed.add(self.current)
            self.retry_at = now + 5
            return
        self.play(now)


class ClockDesignModels(unittest.TestCase):
    def setUp(self):
        self.utc = datetime(2026, 10, 14, 14, 59, 30, tzinfo=timezone.utc)

    def test_jst_rollover(self):
        self.assertAlmostEqual(jst(self.utc), 23 + 59 / 60 + 30 / 3600)
        midnight = self.utc.replace(hour=15, minute=0, second=0)
        self.assertEqual(jst(midnight), 0)

    def test_manual_is_static_and_wraps_in_both_directions(self):
        c = ClockModel()
        c.manual(-1)
        self.assertEqual(c.hour(50000, self.utc), 23)
        c.manual(24)
        self.assertEqual(c.hour(90000, self.utc), 0)

    def test_auto_is_true_jst_not_local_elapsed(self):
        c = ClockModel(anchor_hour=3, anchor_server=900)
        c.auto()
        self.assertEqual(c.hour(900, self.utc), jst(self.utc))
        self.assertEqual(c.hour(-1000, self.utc), jst(self.utc))

    def test_acceleration_begins_from_jst_not_manual_hour(self):
        c = ClockModel(manual_hour=7)
        c.cycle(100, self.utc)
        self.assertEqual(c.speed, 2)
        self.assertAlmostEqual(c.anchor_hour, jst(self.utc))
        self.assertAlmostEqual(c.hour(160, self.utc), wrap(jst(self.utc) + 120 / 3600))

    def test_speed_change_preserves_simulated_instant(self):
        c = ClockModel()
        c.cycle(100, self.utc)
        before = c.hour(200, self.utc)
        c.cycle(200, self.utc)
        self.assertEqual(c.speed, 5)
        self.assertAlmostEqual(c.hour(200, self.utc), before)
        self.assertAlmostEqual(c.hour(260, self.utc), wrap(before + 300 / 3600))

    def test_speed_sequence_returns_to_real_jst(self):
        c = ClockModel()
        speeds = []
        for i in range(6):
            c.cycle(i * 1000, self.utc)
            speeds.append(c.speed)
        self.assertEqual(speeds, [2, 5, 10, 30, 60, 1])
        self.assertEqual(c.mode, 1)
        self.assertEqual(c.hour(10000, self.utc), jst(self.utc))

    def test_late_joiner_and_successor_derive_same_hour(self):
        c = ClockModel(mode=2, speed=30, anchor_hour=7.2, anchor_server=100)
        late_joiner = replace(c)
        successor = replace(late_joiner)
        for now in [100, 400, 9000]:
            self.assertEqual(c.hour(now, self.utc), late_joiner.hour(now, self.utc))
            self.assertEqual(c.hour(now, self.utc), successor.hour(now, self.utc))

    def test_owner_departure_before_send_retains_last_replicated_not_uncommitted_edit(self):
        published = ClockModel(mode=2, speed=5, anchor_hour=6, anchor_server=10)
        departing = replace(published)
        departing.manual(20) # not serialized before departure
        successor = replace(published)
        self.assertNotEqual(successor.mode, departing.mode)
        self.assertEqual(successor.hour(60, self.utc), published.hour(60, self.utc))
        # This is the documented limit: unsent/in-flight commands are not durable.

    def test_rebase_is_continuous(self):
        c = ClockModel(mode=2, speed=60, anchor_hour=23.9, anchor_server=100)
        before = c.hour(700, self.utc)
        c.rebase(700, self.utc)
        self.assertAlmostEqual(c.hour(700, self.utc), before)
        self.assertAlmostEqual(c.hour(760, self.utc), wrap(before + 1))

    def test_server_timestamp_wrap_uses_delta_semantics(self):
        before = ((2 ** 31) - 1000) / 1000
        after = (-(2 ** 31) + 1000) / 1000
        self.assertAlmostEqual(server_delta(after, before), 2)

    def test_midnight_visual_shortest_path(self):
        difference = ((.1 - 23.9 + 12) % 24) - 12
        self.assertAlmostEqual(difference, .2)

    def test_keyframe_cycle_is_continuous(self):
        def keys(hour):
            if hour < 6: return 0, 1, hour / 6
            if hour < 12: return 1, 2, (hour - 6) / 6
            if hour < 18.5: return 2, 3, (hour - 12) / 6.5
            return 3, 0, (hour - 18.5) / 5.5
        values = [.04, .6, 1, .7]
        def sample(hour):
            a, b, t = keys(hour % 24)
            t = t * t * (3 - 2 * t)
            return values[a] * (1 - t) + values[b] * t
        for boundary in [0, 6, 12, 18.5, 24]:
            self.assertAlmostEqual(sample(boundary - 1e-5), sample(boundary + 1e-5), places=8)
        self.assertEqual(sample(18.5), values[3])


class SerializationDesignModels(unittest.TestCase):
    def test_many_frames_do_not_spam_network(self):
        s = SerializationModel()
        for frame in range(10000): s.flush(frame / 90)
        self.assertEqual(s.requests, 0)
        s.edit()
        for frame in range(10000): s.flush(frame / 90)
        self.assertEqual(s.requests, 1)

    def test_update_while_queued_is_included_in_pre_serialization_snapshot(self):
        s = SerializationModel()
        s.edit(); s.flush(0); s.edit(); s.pre(); s.post(1)
        self.assertFalse(s.dirty)
        s.flush(2)
        self.assertEqual(s.requests, 1)

    def test_edit_after_snapshot_remains_dirty(self):
        s = SerializationModel()
        s.edit(); s.flush(0); s.pre(); s.edit(); s.post(1); s.flush(1)
        self.assertEqual(s.requests, 2)

    def test_failure_backoff_is_two_seconds(self):
        s = SerializationModel()
        s.edit(); s.flush(0); s.pre(); s.post(1, False)
        s.flush(2.99)
        self.assertEqual(s.requests, 1)
        s.flush(3)
        self.assertEqual(s.requests, 2)

    def test_nonowner_cannot_flush(self):
        s = SerializationModel(dirty=True)
        s.flush(1, owner=False)
        self.assertEqual(s.requests, 0)

    def test_disable_reenable_does_not_wait_forever_for_old_queue(self):
        s = SerializationModel()
        s.edit(); s.flush(0)
        self.assertTrue(s.queued)
        s.disable(); s.enable(owner=True); s.flush(1)
        self.assertEqual(s.requests, 2)

    def test_transfer_marks_only_new_owner_dirty(self):
        s = SerializationModel(dirty=True, queued=True)
        s.transfer(False)
        self.assertFalse(s.dirty)
        s.transfer(True)
        s.flush(10)
        self.assertEqual(s.requests, 1)


class BgmDesignModels(unittest.TestCase):
    def test_default_off_and_empty_all_null_are_noop(self):
        for clips in [[], [None], [None, 0, .1]]:
            bgm = BgmModel(clips)
            self.assertFalse(bgm.on)
            bgm.enable(0)
            for t in range(100): bgm.tick(t)
            self.assertEqual(bgm.starts, [])

    def test_missing_source_is_safe(self):
        bgm = BgmModel([60], source=False)
        bgm.enable(0); bgm.tick(10)
        self.assertEqual(bgm.starts, [])

    def test_single_clip_repeats_after_real_playback(self):
        bgm = BgmModel([4])
        bgm.enable(0); bgm.tick(1, playing=True); bgm.tick(4)
        self.assertEqual(bgm.starts, [(0, 0), (4, 0)])

    def test_multiple_tracks_never_repeat_immediately(self):
        bgm = BgmModel([30, None, 40, 50])
        bgm.on = True
        rng = random.Random(7)
        for t in range(200): bgm.play(t, rng)
        indices = [i for _, i in bgm.starts]
        self.assertNotIn(1, indices)
        self.assertTrue(all(a != b for a, b in zip(indices, indices[1:])))

    def test_long_failed_clip_advances_after_grace_and_backoff_not_full_duration(self):
        bgm = BgmModel([600, 700])
        bgm.enable(0)
        failed = bgm.current
        bgm.tick(3)
        self.assertEqual(bgm.retry_at, 8)
        bgm.tick(7.99)
        self.assertEqual(len(bgm.starts), 1)
        bgm.tick(8)
        self.assertEqual(len(bgm.starts), 2)
        self.assertNotEqual(bgm.current, failed)
        self.assertEqual(bgm.retry_at, 0)

    def test_short_failed_clip_is_also_quarantined(self):
        bgm = BgmModel([.2])
        bgm.enable(0); bgm.tick(3); bgm.tick(8)
        self.assertTrue(bgm.all_failed)
        self.assertEqual(len(bgm.starts), 1)

    def test_late_decoder_recovery_cancels_backoff(self):
        bgm = BgmModel([600])
        bgm.enable(0); bgm.tick(3)
        bgm.tick(4, playing=True)
        self.assertEqual(bgm.retry_at, 0)
        self.assertEqual(bgm.failed, set())
        bgm.tick(8, playing=True)
        self.assertEqual(len(bgm.starts), 1)

    def test_all_failed_stops_retry_until_explicit_reenable(self):
        bgm = BgmModel([600])
        bgm.enable(0); bgm.tick(3); bgm.tick(8)
        self.assertTrue(bgm.all_failed)
        bgm.tick(10000)
        self.assertEqual(len(bgm.starts), 1)
        bgm.enable(10001)
        self.assertFalse(bgm.all_failed)
        self.assertEqual(len(bgm.starts), 2)

    def test_disable_during_backoff_does_not_restart(self):
        bgm = BgmModel([600])
        bgm.enable(0); bgm.tick(3)
        bgm.on = False; bgm.retry_at = 0
        bgm.tick(8)
        self.assertEqual(len(bgm.starts), 1)


if __name__ == '__main__':
    unittest.main()
