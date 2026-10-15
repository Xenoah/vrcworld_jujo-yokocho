"""Portable source/contract checks, not a Unity or Udon execution test.

Run with the pinned parser dependencies installed:
    python -m unittest discover -s Tests -p 'test_runtime_*.py' -v
"""
from pathlib import Path
import re
import unittest
import uuid

from tree_sitter import Language, Parser
import tree_sitter_c_sharp

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'Assets' / 'TreeTopYokochoEntrySystems' / 'Runtime'
PARSER = Parser(Language(tree_sitter_c_sharp.language()))


def source(name):
    return (RUNTIME / (name + '.cs')).read_text(encoding='utf-8')


def method(text, name):
    """Use parsed AST boundaries, not regex brace counting, for source checks."""
    raw = text.encode()
    tree = PARSER.parse(raw)
    found = []
    def visit(node):
        if node.type == 'method_declaration':
            identifier = node.child_by_field_name('name')
            if identifier and raw[identifier.start_byte:identifier.end_byte].decode() == name:
                found.append(raw[node.start_byte:node.end_byte].decode())
        for child in node.children:
            visit(child)
    visit(tree.root_node)
    if len(found) != 1:
        raise AssertionError(f'Expected one method {name}, got {len(found)}')
    return found[0]


class RuntimeSourceContracts(unittest.TestCase):
    def setUp(self):
        self.clock = source('YokochoGlobalClock')
        self.bgm = source('YokochoBgmController')
        self.relay = source('YokochoEntryControl')

    def test_all_three_scripts_parse_without_errors(self):
        files = sorted(RUNTIME.glob('*.cs'))
        self.assertEqual(len(files), 3)
        for path in files:
            tree = PARSER.parse(path.read_bytes())
            self.assertFalse(tree.root_node.has_error, path.name)
            self.assertIn(f'public class {path.stem} : UdonSharpBehaviour', path.read_text())

    def test_runtime_file_meta_guids_are_stable_and_unique(self):
        guids = []
        for path in RUNTIME.glob('*.cs'):
            actual = re.search(r'^guid: ([0-9a-f]{32})$', Path(str(path) + '.meta').read_text(), re.M).group(1)
            expected = uuid.uuid5(uuid.NAMESPACE_URL,
                'https://treetopyokocho.local/entry-runtime/v1/' + path.relative_to(ROOT / 'Assets').as_posix()).hex
            self.assertEqual(actual, expected)
            guids.append(actual)
        self.assertEqual(len(guids), len(set(guids)))

    def test_only_clock_has_synced_state(self):
        self.assertIn('BehaviourSyncMode.Manual', self.clock)
        self.assertEqual(self.clock.count('[UdonSynced]'), 6)
        for local in (self.bgm, self.relay):
            self.assertIn('BehaviourSyncMode.None', local)
            self.assertNotIn('UdonSynced', local)
            self.assertNotIn('SendCustomNetworkEvent', local)
            self.assertNotIn('RequestSerialization', local)

    def test_button_events_are_local_only(self):
        names = ['_PreviousHour', '_NextHour', '_SetDawn', '_SetNoon', '_SetDusk',
                 '_SetMidnight', '_SetAuto', '_CycleSpeed', '_ResetDusk']
        for name in names:
            self.assertIn('RequestOwnerCommand(', method(self.clock, name))
        for name in ['_ToggleMusic', '_EnableMusic', '_DisableMusic', '_NextTrack']:
            self.assertIn(f'void {name}(', self.bgm)
        self.assertIn('eventName.StartsWith("_")', method(self.relay, 'Interact'))
        self.assertNotIn('NetworkCallable', self.relay)

    def test_owner_commands_explicitly_allowlisted_and_bounded(self):
        names = re.findall(r'\[NetworkCallable\(maxEventsPerSecond: 4\)\]\s+public void (\w+)\(', self.clock)
        self.assertEqual(set(names), {'OwnerPreviousHour', 'OwnerNextHour', 'OwnerSetDawn', 'OwnerSetNoon',
                                     'OwnerSetDusk', 'OwnerSetMidnight', 'OwnerSetAuto', 'OwnerCycleSpeed'})
        for name in names:
            self.assertIn('AcceptOwnerCommand()', method(self.clock, name))
        accept = method(self.clock, 'AcceptOwnerCommand')
        self.assertIn('Networking.IsOwner(gameObject)', accept)
        self.assertIn('Time.time < nextOwnerCommand', accept)
        self.assertIn('Time.time + 0.25f', accept)
        self.assertNotIn('SetOwner(', self.clock)
        self.assertNotIn('IsMaster', self.clock)

    def test_clock_uses_network_time_not_device_wall_clock(self):
        body = method(self.clock, 'NetworkJstHour')
        body = re.sub(r'//[^\n]*', '', body)
        self.assertIn('Networking.GetNetworkDateTime()', body)
        self.assertIn('utc.Hour + 9.0', body)
        self.assertNotIn('DateTime.Now', body)
        self.assertNotIn('DateTime.UtcNow', body)
        self.assertNotIn('ToLocalTime', body)
        self.assertIn('Networking.CalculateServerDeltaTime(', method(self.clock, 'CurrentHour'))

    def test_mode_and_speed_contract(self):
        speed = method(self.clock, 'OwnerCycleSpeed')
        self.assertIn('clockMode == 2 ? CurrentHour() : NetworkJstHour()', speed)
        self.assertIn('anchorServerSeconds = Networking.GetServerTimeInSeconds()', speed)
        for value in ['2f', '5f', '10f', '30f', '60f', '1f']:
            self.assertIn(value, speed)
        auto = method(self.clock, 'OwnerSetAuto')
        self.assertIn('clockMode = 1', auto)
        self.assertIn('clockSpeed = 1f', auto)

    def test_late_join_and_owner_transfer_do_not_reset_synced_state(self):
        transfer = method(self.clock, 'OnOwnershipTransferred')
        for field in ['clockInitialized', 'clockMode', 'manualHour', 'clockSpeed', 'anchorHour', 'anchorServerSeconds']:
            self.assertNotRegex(transfer, rf'\b{field}\s*=(?!=)')
        receive = method(self.clock, 'OnDeserialization')
        self.assertNotIn('SendCustomNetworkEvent', receive)
        self.assertNotIn('RequestSerialization', receive)
        init = method(self.clock, 'MaintainOwnerState')
        self.assertIn('!Networking.IsNetworkSettled', init)
        self.assertIn('if (!clockInitialized)', init)

    def test_serialization_is_coalesced_and_failure_retries_are_bounded(self):
        self.assertEqual(self.clock.count('RequestSerialization();'), 1)
        flush = method(self.clock, 'FlushState')
        for gate in ['!stateDirty', 'sendQueued', 'Time.time < nextSend', '!Networking.IsOwner(gameObject)']:
            self.assertIn(gate, flush)
        self.assertIn('stateDirty = false', method(self.clock, 'OnPreSerialization'))
        post = method(self.clock, 'OnPostSerialization')
        self.assertIn('!result.success', post)
        self.assertIn('stateDirty = true', post)
        self.assertIn('Time.time + 2f', post)
        self.assertIn('elapsed >= 600.0', method(self.clock, 'MaintainOwnerState'))
        self.assertNotIn('RequestSerialization', method(self.clock, 'ApplyAtmosphere'))

    def test_runtime_sky_and_ambient_are_not_just_numeric_clock(self):
        body = method(self.clock, 'ApplyAtmosphere')
        for value in ['ambientSkyColor', 'ambientEquatorColor', 'ambientGroundColor', 'fogColor',
                      'sun.transform.rotation', 'sun.color', 'sun.intensity',
                      '"_Zenith"', '"_Horizon"', '"_SunsetColor"', '"_HighCloudTint"',
                      '"_SunsetDirection"', '"_StarStrength"', '"_AuroraStrength"']:
            self.assertIn(value, body)
        self.assertNotIn('fillLight.', body)
        for banned in ['Lightmapping.', 'DynamicGI.', 'LightProbes.', 'RenderProbe(', 'LightType.Point',
                       'lightmapBakeType =', 'new Material(']:
            self.assertNotIn(banned, self.clock)

    def test_baseline_snapshot_and_restore_is_complete(self):
        restore = method(self.clock, 'OnDisable')
        for value in ['originalSky', 'originalSun', 'baseAmbientSky', 'baseAmbientEquator', 'baseAmbientGround',
                      'baseAmbientIntensity', 'baseFogColor', 'baseFogDensity', 'baseSunRotation',
                      'baseSunColor', 'baseSunIntensity', 'baseZenith', 'baseHorizon', 'baseSunset',
                      'baseCloudTint', 'baseSunsetDirection', 'baseSkyStrength', 'baseStars', 'baseAurora']:
            self.assertIn(value, restore)
        self.assertIn('captured = false', restore)
        self.assertIn('hour == 18.5f', method(self.clock, 'ApplyAtmosphere'))
        self.assertIn('CaptureBaseline()', method(self.clock, 'OnEnable'))

    def test_bgm_default_off_and_empty_playlist_are_safe(self):
        self.assertIn('defaultOn = false', self.bgm)
        self.assertIn('new AudioClip[0]', self.bgm)
        self.assertIn('validCount == 0', method(self.bgm, 'PlayRandom'))
        self.assertIn('NO MP3', method(self.bgm, 'UpdateStatus'))
        self.assertIn('SOURCE NOT SET', method(self.bgm, 'UpdateStatus'))
        self.assertIn('playlist[index] != null', method(self.bgm, 'IsValidClip'))

    def test_bgm_backoff_regression_branch_order(self):
        body = method(self.bgm, 'Update')
        retry = body.index('if (retryAt > 0f)', body.index('nextPoll ='))
        failure = body.index('if (!sawPlayback || Time.time + 1f < expectedEnd)')
        self.assertLess(retry, failure)
        self.assertIn('retryAt = 0f;\n            PlayRandom();\n            return;', body)
        self.assertIn('failedClips[currentTrack] = true', body)
        self.assertIn('Time.time + 5f', body)

    def test_bgm_failed_clips_terminate_and_reenable_can_retry(self):
        play = method(self.bgm, 'PlayRandom')
        self.assertIn('if (choices == 0)', play)
        self.assertIn('allFailed = true', play)
        self.assertIn('ResetFailures()', method(self.bgm, '_EnableMusic'))
        self.assertIn('allFailed', method(self.bgm, 'Update'))
        self.assertIn('OFF > ON TO RETRY', method(self.bgm, 'UpdateStatus'))

    def test_bgm_random_nonrepeat_and_quiet_fade(self):
        play = method(self.bgm, 'PlayRandom')
        self.assertIn('choices > 1', play)
        self.assertIn('Random.Range(0, choices)', play)
        self.assertIn('excludePrevious && i == currentTrack', play)
        self.assertIn('Mathf.MoveTowards', method(self.bgm, 'Update'))
        self.assertIn('musicSource.Stop()', method(self.bgm, 'OnDisable'))

    def test_status_text_is_printable_ascii(self):
        for script in [self.clock, self.bgm]:
            for literal in re.findall(r'"([^"\n]*)"', method(script, 'UpdateStatus')):
                self.assertTrue(all(32 <= ord(c) <= 126 for c in literal), literal)

    def test_disable_reenable_clears_stale_send_queue(self):
        self.assertIn('sendQueued = false', method(self.clock, 'OnDisable'))
        enable = method(self.clock, 'OnEnable')
        self.assertIn('sendQueued = false', enable)
        self.assertIn('MarkStateDirty()', enable)
        self.assertNotIn('clockMode =', enable)
        self.assertNotIn('anchorHour =', enable)

    def test_installation_markers_are_not_network_state(self):
        self.assertIn('public string installationVersion = "0.1.0"', self.clock)
        self.assertIn('public string installedCoreManifestSha256 = ""', self.clock)
        self.assertNotRegex(self.clock, r'\[UdonSynced\]\s+public string')


if __name__ == '__main__':
    unittest.main()
