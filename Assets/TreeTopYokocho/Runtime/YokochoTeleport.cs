using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class YokochoTeleport : UdonSharpBehaviour
{
    public Transform destination;
    public YokochoSafety recovery;
    private float nextUse;

    public override void Interact()
    {
        VRCPlayerApi player = Networking.LocalPlayer;
        if (!Utilities.IsValid(player) || destination == null || Time.time < nextUse) return;
        nextUse = Time.time + 0.6f;
        player.SetVelocity(Vector3.zero);
        player.TeleportTo(destination.position, destination.rotation);
        SendCustomEventDelayedSeconds(nameof(ConfirmArrival), 0.1f);
    }
    // Stations may reject TeleportTo. Only change the recovery checkpoint after
    // the local player actually arrives, rather than trusting the button click.
    public void ConfirmArrival()
    {
        VRCPlayerApi player = Networking.LocalPlayer;
        if (!Utilities.IsValid(player) || destination == null || recovery == null) return;
        if (Vector3.Distance(player.GetPosition(), destination.position) < 1.0f)
            recovery.SetSafeDestination(destination);
    }
}
