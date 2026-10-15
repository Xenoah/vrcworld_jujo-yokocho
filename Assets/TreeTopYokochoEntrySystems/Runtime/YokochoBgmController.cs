using UdonSharp;
using UnityEngine;

// LOCAL listening preference. Intentionally no synchronized music state.
// Installer populates imported MP3 clips only; canopy/wind ambience is separate.
[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class YokochoBgmController : UdonSharpBehaviour
{
    public AudioSource musicSource;
    public AudioClip[] playlist = new AudioClip[0];
    public TextMesh statusText;
    public bool defaultOn = false;
    [Range(0f, 0.5f)] public float volume = 0.22f;
    [Range(0.2f, 3f)] public float fadeSeconds = 0.8f;

    private bool started;
    private bool isOn;
    private bool[] failedClips;
    private int currentTrack = -1;
    private int validCount;
    private bool sawPlayback;
    private bool allFailed;
    private float attemptedAt;
    private float expectedEnd;
    private float retryAt;
    private float nextPoll;

    private void Start()
    {
        started = true;
        isOn = defaultOn;
        ResetFailures();
        if (musicSource != null)
        {
            musicSource.playOnAwake = false;
            musicSource.loop = false;
            musicSource.pitch = 1f;
            musicSource.volume = 0f;
            musicSource.Stop();
        }
        if (isOn) PlayRandom();
        UpdateStatus();
    }

    private void OnEnable()
    {
        if (!started) return;
        ResetFailures();
        if (isOn) PlayRandom();
        UpdateStatus();
    }

    private void Update()
    {
        if (!started) return;
        if (musicSource != null)
        {
            float targetVolume = isOn ? Mathf.Clamp(volume, 0f, 0.5f) : 0f;
            musicSource.volume = Mathf.MoveTowards(musicSource.volume, targetVolume,
                Time.deltaTime * Mathf.Max(0.01f, Mathf.Clamp(volume, 0f, 0.5f))
                / Mathf.Max(0.2f, fadeSeconds));
            if (!isOn && musicSource.volume < 0.0001f && musicSource.isPlaying)
                musicSource.Stop();
        }
        if (isOn && musicSource != null && musicSource.isPlaying)
        {
            sawPlayback = true;
            if (retryAt > 0f)
            {
                // A slow decoder can recover during the backoff. Keep that song.
                retryAt = 0f;
                if (currentTrack >= 0 && failedClips != null && currentTrack < failedClips.Length)
                    failedClips[currentTrack] = false;
                UpdateStatus();
            }
        }
        if (Time.time < nextPoll) return;
        nextPoll = Time.time + 0.25f;
        if (!isOn || musicSource == null || validCount == 0 || allFailed) return;

        // Handle an expired backoff BEFORE detecting a stopped long clip again.
        // Otherwise a 10-minute clip that never started could keep deferring retry.
        if (retryAt > 0f)
        {
            if (Time.time < retryAt) return;
            retryAt = 0f;
            PlayRandom();
            return;
        }
        if (musicSource.isPlaying)
        {
            sawPlayback = true;
            return;
        }
        if (Time.time < attemptedAt + 3f) return; // asynchronous decoder grace
        if (!sawPlayback || Time.time + 1f < expectedEnd)
        {
            if (currentTrack >= 0 && currentTrack < failedClips.Length)
                failedClips[currentTrack] = true;
            retryAt = Time.time + 5f;
            UpdateStatus();
            return;
        }
        PlayRandom(); // observed completion; randomly choose next valid clip
    }

    private void ResetFailures()
    {
        failedClips = new bool[playlist == null ? 0 : playlist.Length];
        allFailed = false;
        retryAt = 0f;
        CountTracks();
    }

    private bool IsValidClip(int index)
    {
        return playlist != null && index >= 0 && index < playlist.Length
            && playlist[index] != null && playlist[index].length > 0.1f;
    }

    private void CountTracks()
    {
        validCount = 0;
        if (playlist == null) return;
        for (int i = 0; i < playlist.Length; i++)
            if (IsValidClip(i)) validCount++;
    }

    private void PlayRandom()
    {
        CountTracks();
        if (musicSource == null || validCount == 0)
        {
            if (musicSource != null) musicSource.Stop();
            currentTrack = -1;
            UpdateStatus();
            return;
        }
        // Inspector/program playlist replacement remains safe; no out-of-range flags.
        if (failedClips == null || failedClips.Length != playlist.Length) ResetFailures();
        int choices = 0;
        for (int i = 0; i < playlist.Length; i++)
            if (IsValidClip(i) && !failedClips[i]) choices++;
        if (choices == 0)
        {
            allFailed = true;
            musicSource.Stop();
            UpdateStatus();
            return;
        }
        bool excludePrevious = choices > 1 && IsValidClip(currentTrack) && !failedClips[currentTrack];
        if (excludePrevious) choices--;
        int selected = Random.Range(0, choices);
        int chosen = -1;
        for (int i = 0; i < playlist.Length; i++)
        {
            if (!IsValidClip(i) || failedClips[i] || (excludePrevious && i == currentTrack)) continue;
            if (selected == 0) { chosen = i; break; }
            selected--;
        }
        if (chosen < 0) return;
        currentTrack = chosen;
        sawPlayback = false;
        allFailed = false;
        retryAt = 0f;
        musicSource.Stop();
        musicSource.clip = playlist[chosen];
        musicSource.loop = false;
        musicSource.pitch = 1f;
        musicSource.volume = 0f;
        attemptedAt = Time.time;
        expectedEnd = Time.time + playlist[chosen].length;
        musicSource.Play();
        UpdateStatus();
    }

    private void UpdateStatus()
    {
        if (statusText == null) return;
        if (musicSource == null) { statusText.text = "BGM LOCAL / SOURCE NOT SET"; return; }
        if (validCount == 0)
        {
            statusText.text = isOn ? "BGM LOCAL ON / NO MP3" : "BGM LOCAL OFF / NO MP3";
            return;
        }
        if (!isOn) { statusText.text = "BGM LOCAL OFF"; return; }
        if (allFailed) { statusText.text = "BGM LOCAL / AUDIO ERROR\nOFF > ON TO RETRY"; return; }
        if (retryAt > 0f) { statusText.text = "BGM LOCAL / RETRY WAIT"; return; }
        statusText.text = "BGM LOCAL ON / RANDOM";
    }

    public void _ToggleMusic() { if (isOn) _DisableMusic(); else _EnableMusic(); }
    public void _EnableMusic()
    {
        if (!started) return;
        isOn = true;
        ResetFailures();
        if (musicSource == null || !musicSource.isPlaying) PlayRandom();
        UpdateStatus();
    }
    public void _DisableMusic()
    {
        isOn = false;
        retryAt = 0f;
        UpdateStatus();
    }
    public void _NextTrack()
    {
        if (!started || !isOn) return;
        if (allFailed) ResetFailures();
        PlayRandom();
    }

    private void OnDisable()
    {
        if (musicSource != null) musicSource.Stop();
    }
}
