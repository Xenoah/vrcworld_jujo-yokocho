using System;
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;
using VRC.SDK3.UdonNetworkCalling;
using VRC.Udon.Common;
using VRC.Udon.Common.Interfaces;

// One owner writes retained state. Visitors send bounded owner commands, never
// take ownership or write network state from UI/deserialization callbacks.
[UdonBehaviourSyncMode(BehaviourSyncMode.Manual)]
public class YokochoGlobalClock : UdonSharpBehaviour
{
    public Light sun;
    public Light fillLight; // Baseline identification only. Baked fill is not animated.
    public Material skyMaterial; // Dedicated add-on clone, never the core Sky.mat.
    public TextMesh statusText;
    [Range(0f, 24f)] public float initialHour = 18.5f;
    public bool startInAuto = false;
    public string installationVersion = "0.1.0";
    public string installedCoreManifestSha256 = "";

    [UdonSynced] private bool clockInitialized;
    [UdonSynced] private int clockMode; // 0 manual; 1 real JST; 2 accelerated.
    [UdonSynced] private float manualHour = 18.5f;
    [UdonSynced] private float clockSpeed = 1f;
    [UdonSynced] private double anchorHour;
    [UdonSynced] private double anchorServerSeconds;

    private bool started;
    private bool captured;
    private bool stateDirty;
    private bool sendQueued;
    private float nextSend;
    private float nextOwnerPoll;
    private float nextLocalCommand;
    private float nextOwnerCommand;
    private float nextVisualTick;
    private float nextStatusTick;
    private float lastVisualTime;
    private float shownHour = 18.5f;
    private Material originalSky;
    private Light originalSun;
    private Quaternion baseSunRotation;
    private Color baseSunColor;
    private float baseSunIntensity;
    private Color baseAmbientSky, baseAmbientEquator, baseAmbientGround;
    private float baseAmbientIntensity;
    private Color baseFogColor;
    private float baseFogDensity;
    private Vector4 baseZenith, baseHorizon, baseSunset, baseCloudTint, baseSunsetDirection;
    private float baseSkyStrength, baseStars, baseAurora;
    private bool hasSky, hasStars, hasAurora;

    private void Start()
    {
        started = true;
        CaptureBaseline();
        shownHour = WrapHour(initialHour);
        lastVisualTime = Time.time;
        ApplyAtmosphere(shownHour);
        UpdateStatus();
    }
    private void OnEnable()
    {
        if (!started) return;
        CaptureBaseline();
        shownHour = CurrentHour();
        lastVisualTime = Time.time;
        ApplyAtmosphere(shownHour);
        sendQueued = false;
        nextOwnerPoll = 0f;
        if (clockInitialized && Networking.IsOwner(gameObject)) MarkStateDirty();
    }

    private float WrapHour(double hour)
    {
        double wrapped = hour % 24.0;
        if (wrapped < 0.0) wrapped += 24.0;
        float result = (float)wrapped;
        return result >= 24f ? 0f : result; // float rounding very close to midnight
    }
    private float NetworkJstHour()
    {
        // SDK network UTC, not each visitor's local system clock. Do not use
        // DateTime.Now/UtcNow or an assumed device timezone as the shared authority.
        DateTime utc = Networking.GetNetworkDateTime();
        return WrapHour(utc.Hour + 9.0 + utc.Minute / 60.0 + utc.Second / 3600.0
            + utc.Millisecond / 3600000.0);
    }
    private float CurrentHour()
    {
        if (!clockInitialized) return WrapHour(initialHour);
        if (clockMode == 1) return NetworkJstHour();
        if (clockMode == 2)
        {
            double elapsed = Networking.CalculateServerDeltaTime(
                Networking.GetServerTimeInSeconds(), anchorServerSeconds);
            if (elapsed < 0.0) elapsed = 0.0; // brief server-clock settling jitter
            return WrapHour(anchorHour + elapsed * clockSpeed / 3600.0);
        }
        return WrapHour(manualHour);
    }

    private void Update()
    {
        if (!started || !captured) return;
        // Local polling is cheap; network sends happen only for dirty state.
        if (Time.time >= nextOwnerPoll)
        {
            nextOwnerPoll = Time.time + 1f;
            MaintainOwnerState();
        }
        FlushState();
        if (Time.time < nextVisualTick) return;
        nextVisualTick = Time.time + 0.1f;
        float elapsed = Mathf.Clamp(Time.time - lastVisualTime, 0f, 1f);
        lastVisualTime = Time.time;
        float target = CurrentHour();
        float difference = Mathf.DeltaAngle(shownHour * 15f, target * 15f) / 15f;
        if (Mathf.Abs(difference) < 0.0001f) shownHour = target;
        else shownHour = WrapHour(shownHour + difference * (1f - Mathf.Exp(-elapsed * 2.5f)));
        ApplyAtmosphere(shownHour);
        if (Time.time >= nextStatusTick)
        {
            nextStatusTick = Time.time + 1f;
            UpdateStatus();
        }
    }

    private void MaintainOwnerState()
    {
        if (!Networking.IsOwner(gameObject) || !Networking.IsNetworkSettled) return;
        if (!clockInitialized)
        {
            // IsNetworkSettled prevents a late joiner from overwriting retained state.
            clockInitialized = true;
            manualHour = WrapHour(initialHour);
            clockMode = startInAuto ? 1 : 0;
            clockSpeed = 1f;
            anchorHour = NetworkJstHour();
            anchorServerSeconds = Networking.GetServerTimeInSeconds();
            MarkStateDirty();
        }
        else if (clockMode == 2)
        {
            double now = Networking.GetServerTimeInSeconds();
            double elapsed = Networking.CalculateServerDeltaTime(now, anchorServerSeconds);
            if (elapsed >= 600.0)
            {
                // Ten-minute rebase bounds timestamp wrap exposure and precision loss.
                // It does not change the displayed simulation time or multiplier.
                anchorHour = WrapHour(anchorHour + elapsed * clockSpeed / 3600.0);
                anchorServerSeconds = now;
                MarkStateDirty();
            }
        }
    }

    private void RequestOwnerCommand(string command)
    {
        if (!clockInitialized || !Networking.IsNetworkSettled || Time.time < nextLocalCommand) return;
        nextLocalCommand = Time.time + 0.4f;
        SendCustomNetworkEvent(NetworkEventTarget.Owner, command);
    }
    // Underscore-prefixed local APIs are not legacy-network-callable.
    public void _PreviousHour() { RequestOwnerCommand(nameof(OwnerPreviousHour)); }
    public void _NextHour() { RequestOwnerCommand(nameof(OwnerNextHour)); }
    public void _SetDawn() { RequestOwnerCommand(nameof(OwnerSetDawn)); }
    public void _SetNoon() { RequestOwnerCommand(nameof(OwnerSetNoon)); }
    public void _SetDusk() { RequestOwnerCommand(nameof(OwnerSetDusk)); }
    public void _SetMidnight() { RequestOwnerCommand(nameof(OwnerSetMidnight)); }
    public void _SetAuto() { RequestOwnerCommand(nameof(OwnerSetAuto)); }
    public void _CycleSpeed() { RequestOwnerCommand(nameof(OwnerCycleSpeed)); }
    public void _ResetDusk() { RequestOwnerCommand(nameof(OwnerSetDusk)); }

    private bool AcceptOwnerCommand()
    {
        // Aggregate bound across all handlers/callers, including local loopback.
        // Anyone may use the controls; this is not an administrative permission gate.
        if (!started || !enabled || !gameObject.activeInHierarchy || !clockInitialized
            || !Networking.IsOwner(gameObject) || Time.time < nextOwnerCommand) return false;
        nextOwnerCommand = Time.time + 0.25f;
        return true;
    }
    private void SetManual(float hour)
    {
        manualHour = WrapHour(hour);
        clockMode = 0;
        clockSpeed = 1f;
        MarkStateDirty();
    }
    [NetworkCallable(maxEventsPerSecond: 4)]
    public void OwnerPreviousHour() { if (AcceptOwnerCommand()) SetManual(CurrentHour() - 1f); }
    [NetworkCallable(maxEventsPerSecond: 4)]
    public void OwnerNextHour() { if (AcceptOwnerCommand()) SetManual(CurrentHour() + 1f); }
    [NetworkCallable(maxEventsPerSecond: 4)]
    public void OwnerSetDawn() { if (AcceptOwnerCommand()) SetManual(6f); }
    [NetworkCallable(maxEventsPerSecond: 4)]
    public void OwnerSetNoon() { if (AcceptOwnerCommand()) SetManual(12f); }
    [NetworkCallable(maxEventsPerSecond: 4)]
    public void OwnerSetDusk() { if (AcceptOwnerCommand()) SetManual(18.5f); }
    [NetworkCallable(maxEventsPerSecond: 4)]
    public void OwnerSetMidnight() { if (AcceptOwnerCommand()) SetManual(0f); }
    [NetworkCallable(maxEventsPerSecond: 4)]
    public void OwnerSetAuto()
    {
        if (!AcceptOwnerCommand()) return;
        clockMode = 1;
        clockSpeed = 1f;
        MarkStateDirty();
    }
    [NetworkCallable(maxEventsPerSecond: 4)]
    public void OwnerCycleSpeed()
    {
        if (!AcceptOwnerCommand()) return;
        float previous = clockMode == 2 ? clockSpeed : 1f;
        float next = previous < 2f ? 2f : previous < 5f ? 5f : previous < 10f ? 10f
            : previous < 30f ? 30f : previous < 60f ? 60f : 1f;
        if (next == 1f)
        {
            clockMode = 1; // 1x means actual JST again, not an offset timeline.
            clockSpeed = 1f;
        }
        else
        {
            // First accelerated step starts from real JST; later changes preserve
            // the simulated instant and change only its future rate.
            anchorHour = clockMode == 2 ? CurrentHour() : NetworkJstHour();
            anchorServerSeconds = Networking.GetServerTimeInSeconds();
            clockMode = 2;
            clockSpeed = next;
        }
        MarkStateDirty();
    }

    private void MarkStateDirty()
    {
        stateDirty = true;
        UpdateStatus();
    }
    private void FlushState()
    {
        if (!stateDirty || sendQueued || Time.time < nextSend
            || !Networking.IsOwner(gameObject) || !Networking.IsNetworkSettled) return;
        sendQueued = true;
        nextSend = Time.time + 0.25f;
        RequestSerialization();
    }
    public override void OnPreSerialization()
    {
        // Mark exactly the snapshot being sent as handled. Changes after this
        // callback mark it dirty again, so a delayed send cannot erase new input.
        stateDirty = false;
    }
    public override void OnPostSerialization(SerializationResult result)
    {
        sendQueued = false;
        if (!result.success && Networking.IsOwner(gameObject))
        {
            stateDirty = true;
            nextSend = Time.time + 2f; // bounded retry of latest state, no busy loop
        }
    }
    public override void OnDeserialization()
    {
        // Applying state never emits commands or requests ownership.
        UpdateStatus();
    }
    public override void OnOwnershipTransferred(VRCPlayerApi newOwner)
    {
        // Keep all synchronized fields unchanged, including the time anchor.
        sendQueued = false;
        stateDirty = false;
        nextOwnerPoll = 0f;
        if (Utilities.IsValid(newOwner) && newOwner.isLocal && clockInitialized)
            MarkStateDirty();
        UpdateStatus();
    }

    private void UpdateStatus()
    {
        if (statusText == null) return;
        if (!clockInitialized) { statusText.text = "TIME GLOBAL / CONNECTING"; return; }
        int minutes = Mathf.FloorToInt(CurrentHour() * 60f) % 1440;
        string time = (minutes / 60).ToString("00") + ":" + (minutes % 60).ToString("00");
        string mode = clockMode == 0 ? "MANUAL" : clockMode == 1 ? "AUTO JST x1"
            : "JST START x" + clockSpeed.ToString("0");
        statusText.text = "TIME GLOBAL " + time + "\n" + mode;
    }

    private void CaptureBaseline()
    {
        if (captured) return;
        originalSky = RenderSettings.skybox;
        originalSun = RenderSettings.sun;
        baseAmbientSky = RenderSettings.ambientSkyColor;
        baseAmbientEquator = RenderSettings.ambientEquatorColor;
        baseAmbientGround = RenderSettings.ambientGroundColor;
        baseAmbientIntensity = RenderSettings.ambientIntensity;
        baseFogColor = RenderSettings.fogColor;
        baseFogDensity = RenderSettings.fogDensity;
        if (sun != null)
        {
            baseSunRotation = sun.transform.rotation;
            baseSunColor = sun.color;
            baseSunIntensity = sun.intensity;
            RenderSettings.sun = sun;
        }
        hasSky = skyMaterial != null && skyMaterial.HasProperty("_Zenith")
            && skyMaterial.HasProperty("_Horizon") && skyMaterial.HasProperty("_SunsetColor")
            && skyMaterial.HasProperty("_HighCloudTint") && skyMaterial.HasProperty("_SunsetDirection")
            && skyMaterial.HasProperty("_SkyStrength");
        if (hasSky)
        {
            baseZenith = skyMaterial.GetVector("_Zenith");
            baseHorizon = skyMaterial.GetVector("_Horizon");
            baseSunset = skyMaterial.GetVector("_SunsetColor");
            baseCloudTint = skyMaterial.GetVector("_HighCloudTint");
            baseSunsetDirection = skyMaterial.GetVector("_SunsetDirection");
            baseSkyStrength = skyMaterial.GetFloat("_SkyStrength");
            hasStars = skyMaterial.HasProperty("_StarStrength");
            hasAurora = skyMaterial.HasProperty("_AuroraStrength");
            if (hasStars) baseStars = skyMaterial.GetFloat("_StarStrength");
            if (hasAurora) baseAurora = skyMaterial.GetFloat("_AuroraStrength");
            RenderSettings.skybox = skyMaterial;
        }
        captured = true;
    }

    private void ApplyAtmosphere(float hour)
    {
        // Quiet keyframes. Authored dusk values at 18:30 are preserved exactly.
        // Baked lightmaps, baked lanterns/fill and reflection probes never rebake.
        int a;
        int b;
        float t;
        if (hour < 6f) { a = 0; b = 1; t = hour / 6f; }
        else if (hour < 12f) { a = 1; b = 2; t = (hour - 6f) / 6f; }
        else if (hour < 18.5f) { a = 2; b = 3; t = (hour - 12f) / 6.5f; }
        else { a = 3; b = 0; t = (hour - 18.5f) / 5.5f; }
        t = Mathf.SmoothStep(0f, 1f, t);
        RenderSettings.ambientSkyColor = Color.Lerp(AmbientSkyAt(a), AmbientSkyAt(b), t);
        RenderSettings.ambientEquatorColor = Color.Lerp(AmbientEquatorAt(a), AmbientEquatorAt(b), t);
        RenderSettings.ambientGroundColor = Color.Lerp(AmbientGroundAt(a), AmbientGroundAt(b), t);
        RenderSettings.ambientIntensity = baseAmbientIntensity;
        RenderSettings.fogColor = Color.Lerp(FogAt(a), FogAt(b), t);
        RenderSettings.fogDensity = baseFogDensity;
        if (sun != null)
        {
            sun.transform.rotation = Quaternion.Slerp(SunRotationAt(a), SunRotationAt(b), t);
            sun.color = Color.Lerp(SunColorAt(a), SunColorAt(b), t);
            sun.intensity = Mathf.Lerp(SunIntensityAt(a), SunIntensityAt(b), t);
        }
        if (!hasSky) return;
        skyMaterial.SetVector("_Zenith", Vector4.Lerp(ZenithAt(a), ZenithAt(b), t));
        skyMaterial.SetVector("_Horizon", Vector4.Lerp(HorizonAt(a), HorizonAt(b), t));
        skyMaterial.SetVector("_SunsetColor", Vector4.Lerp(SunsetAt(a), SunsetAt(b), t));
        skyMaterial.SetVector("_HighCloudTint", Vector4.Lerp(CloudTintAt(a), CloudTintAt(b), t));
        // Rotate azimuth rather than lerping opposing vectors through zero.
        float angle = Mathf.LerpAngle(SunsetAngleAt(a), SunsetAngleAt(b), t) * Mathf.Deg2Rad;
        if (hour == 18.5f) skyMaterial.SetVector("_SunsetDirection", baseSunsetDirection);
        else skyMaterial.SetVector("_SunsetDirection", new Vector4(Mathf.Sin(angle), 0f, Mathf.Cos(angle), 0f));
        skyMaterial.SetFloat("_SkyStrength", baseSkyStrength);
        float stars = Mathf.Lerp(StarsAt(a), StarsAt(b), t);
        if (hasStars) skyMaterial.SetFloat("_StarStrength", baseStars * stars);
        if (hasAurora) skyMaterial.SetFloat("_AuroraStrength", baseAurora * stars);
    }

    private float StarsAt(int key) { return key == 0 || key == 3 ? 1f : key == 1 ? 0.05f : 0f; }
    private Vector4 ZenithAt(int key)
    {
        if (key == 0) return new Vector4(0.003f, 0.008f, 0.023f, 1f);
        if (key == 1) return new Vector4(0.04f, 0.075f, 0.15f, 1f);
        if (key == 2) return new Vector4(0.055f, 0.16f, 0.38f, 1f);
        return baseZenith;
    }
    private Vector4 HorizonAt(int key)
    {
        if (key == 0) return new Vector4(0.022f, 0.034f, 0.065f, 1f);
        if (key == 1) return new Vector4(0.31f, 0.19f, 0.16f, 1f);
        if (key == 2) return new Vector4(0.48f, 0.62f, 0.82f, 1f);
        return baseHorizon;
    }
    private Vector4 SunsetAt(int key)
    {
        if (key == 0) return baseSunset * 0.04f;
        if (key == 1) return new Vector4(0.32f, 0.13f, 0.055f, 1f);
        if (key == 2) return baseSunset * 0.02f;
        return baseSunset;
    }
    private Vector4 CloudTintAt(int key)
    {
        if (key == 0) return baseCloudTint * 0.5f;
        if (key == 1) return new Vector4(0.026f, 0.02f, 0.023f, 1f);
        if (key == 2) return new Vector4(0.07f, 0.085f, 0.11f, 1f);
        return baseCloudTint;
    }
    private float SunsetAngleAt(int key)
    {
        float dusk = Mathf.Atan2(baseSunsetDirection.x, baseSunsetDirection.z) * Mathf.Rad2Deg;
        return key == 1 ? dusk + 180f : dusk;
    }
    private Color AmbientSkyAt(int key)
    {
        if (key == 0) return baseAmbientSky * 0.32f;
        if (key == 1) return baseAmbientSky * 0.8f;
        if (key == 2) return new Color(0.38f, 0.48f, 0.65f, 1f);
        return baseAmbientSky;
    }
    private Color AmbientEquatorAt(int key)
    {
        if (key == 0) return baseAmbientEquator * 0.32f;
        if (key == 1) return baseAmbientEquator * 0.8f;
        if (key == 2) return new Color(0.38f, 0.40f, 0.43f, 1f);
        return baseAmbientEquator;
    }
    private Color AmbientGroundAt(int key)
    {
        if (key == 0) return baseAmbientGround * 0.32f;
        if (key == 1) return baseAmbientGround * 0.8f;
        if (key == 2) return new Color(0.15f, 0.14f, 0.12f, 1f);
        return baseAmbientGround;
    }
    private Color FogAt(int key)
    {
        // RenderSettings fog colors are Unity Color API/sRGB values, not the
        // scene-linear RGB vectors passed directly to the custom sky shader.
        if (key == 0) return new Color(0.10f, 0.14f, 0.22f, 1f);
        if (key == 1) return new Color(0.59f, 0.47f, 0.44f, 1f);
        if (key == 2) return new Color(0.70f, 0.78f, 0.88f, 1f);
        return baseFogColor;
    }
    private Quaternion SunRotationAt(int key)
    {
        if (key == 0) return Quaternion.Euler(27f, 230f, 0f);
        if (key == 1) return Quaternion.Euler(8f, 80f, 0f);
        if (key == 2) return Quaternion.Euler(65f, 160f, 0f);
        return baseSunRotation;
    }
    private Color SunColorAt(int key)
    {
        if (key == 0) return new Color(0.42f, 0.56f, 0.85f, 1f);
        if (key == 1) return new Color(1f, 0.67f, 0.45f, 1f);
        if (key == 2) return new Color(1f, 0.95f, 0.85f, 1f);
        return baseSunColor;
    }
    private float SunIntensityAt(int key)
    {
        if (key == 0) return baseSunIntensity * 0.16f;
        if (key == 1) return baseSunIntensity * 0.65f;
        if (key == 2) return Mathf.Min(1.1f, baseSunIntensity * 1.45f);
        return baseSunIntensity;
    }

    private void OnDisable()
    {
        if (!captured) return;
        RenderSettings.skybox = originalSky;
        RenderSettings.sun = originalSun;
        RenderSettings.ambientSkyColor = baseAmbientSky;
        RenderSettings.ambientEquatorColor = baseAmbientEquator;
        RenderSettings.ambientGroundColor = baseAmbientGround;
        RenderSettings.ambientIntensity = baseAmbientIntensity;
        RenderSettings.fogColor = baseFogColor;
        RenderSettings.fogDensity = baseFogDensity;
        if (sun != null)
        {
            sun.transform.rotation = baseSunRotation;
            sun.color = baseSunColor;
            sun.intensity = baseSunIntensity;
        }
        if (hasSky)
        {
            skyMaterial.SetVector("_Zenith", baseZenith);
            skyMaterial.SetVector("_Horizon", baseHorizon);
            skyMaterial.SetVector("_SunsetColor", baseSunset);
            skyMaterial.SetVector("_HighCloudTint", baseCloudTint);
            skyMaterial.SetVector("_SunsetDirection", baseSunsetDirection);
            skyMaterial.SetFloat("_SkyStrength", baseSkyStrength);
            if (hasStars) skyMaterial.SetFloat("_StarStrength", baseStars);
            if (hasAurora) skyMaterial.SetFloat("_AuroraStrength", baseAurora);
        }
        captured = false;
        // A disabled behaviour must not remain blocked on an old queued callback.
        // Re-enable re-advertises the retained latest state without resetting it.
        sendQueued = false;
    }
}
