using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

// Renderer-free physical walls are the primary fall protection. This local-only
// fallback checks four times per second, without per-frame Udon or network traffic.
[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class YokochoSafety : UdonSharpBehaviour
{
    public Transform arrival;
    public Collider[] walkableFloors;
    public float minimumHeight = -7f;
    private Vector3 lastSafe;
    private Quaternion lastRotation;
    private bool ready;
    private bool movementConfigured;
    private bool localSeated;
    private float resumeAt;

    private void Start()
    {
        if (arrival == null || walkableFloors == null || walkableFloors.Length == 0)
        {
            Debug.LogError("Yokocho fall recovery has no arrival or walkable floor references.");
            return;
        }
        SetSafeDestination(arrival);
        SendCustomEventDelayedSeconds(nameof(CheckPlayer), 0.25f);
    }

    // All callers use builder-created destinations checked by the editor audit.
    public void SetSafeDestination(Transform target)
    {
        if (target == null) return;
        lastSafe = target.position;
        lastRotation = target.rotation;
        resumeAt = Time.time + 0.6f;
        ready = true;
    }

    public void EnterSeat() { localSeated = true; }
    public void ExitSeat() { localSeated = false; resumeAt = Time.time + 0.6f; }

    private bool IsWalkable(Collider candidate)
    {
        if (!Utilities.IsValid(candidate) || walkableFloors == null) return false;
        for (int i = 0; i < walkableFloors.Length; i++)
            if (candidate == walkableFloors[i]) return true;
        return false;
    }

    private bool HasGroundAt(Vector3 point)
    {
        RaycastHit hit;
        return Physics.Raycast(point + Vector3.up * 0.3f, Vector3.down, out hit,
            0.7f, 1 << 0, QueryTriggerInteraction.Ignore) && IsWalkable(hit.collider);
    }

    public void CheckPlayer()
    {
        VRCPlayerApi p = Networking.LocalPlayer;
        if (ready && Utilities.IsValid(p))
        {
            // LocalPlayer may not exist during Start in every test environment.
            if (!movementConfigured)
            {
                p.SetWalkSpeed(2.1f); p.SetRunSpeed(3.6f); p.SetJumpImpulse(3.0f);
                movementConfigured = true;
            }
            if (!localSeated && Time.time >= resumeAt)
            {
                Vector3 pos = p.GetPosition();
                RaycastHit hit;
                bool overFloor = Physics.Raycast(pos + Vector3.up * 0.16f, Vector3.down, out hit,
                    2.0f, 1 << 0, QueryTriggerInteraction.Ignore) && IsWalkable(hit.collider);
                if (overFloor && p.IsPlayerGrounded() && hit.distance < 0.4f)
                {
                    Vector3 ground = hit.point;
                    // Do not remember an edge as a recovery point. This is a
                    // conservative cross-shaped floor check, not a capsule test.
                    if (HasGroundAt(ground + Vector3.right * 0.22f) && HasGroundAt(ground - Vector3.right * 0.22f)
                        && HasGroundAt(ground + Vector3.forward * 0.22f) && HasGroundAt(ground - Vector3.forward * 0.22f))
                    {
                        lastSafe = ground + Vector3.up * 0.08f;
                        lastRotation = p.GetRotation();
                    }
                }
                if (pos.y < minimumHeight || (!overFloor && pos.y < lastSafe.y - 1.5f && p.GetVelocity().y < -1.0f))
                {
                    p.SetVelocity(Vector3.zero);
                    p.TeleportTo(lastSafe, lastRotation);
                    resumeAt = Time.time + 0.6f;
                }
            }
        }
        SendCustomEventDelayedSeconds(nameof(CheckPlayer), 0.25f);
    }

    public override void OnPlayerRespawn(VRCPlayerApi player)
    {
        if (!Utilities.IsValid(player) || !player.isLocal || arrival == null) return;
        localSeated = false;
        SetSafeDestination(arrival);
    }
}
