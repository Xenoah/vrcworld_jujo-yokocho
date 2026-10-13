using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class YokochoSeat : UdonSharpBehaviour
{
    public YokochoSafety recovery;
    public Transform exitPoint;

    public override void Interact()
    {
        VRCPlayerApi player = Networking.LocalPlayer;
        if (Utilities.IsValid(player)) player.UseAttachedStation();
    }

    public override void OnStationEntered(VRCPlayerApi player)
    {
        if (!Utilities.IsValid(player) || !player.isLocal || recovery == null) return;
        recovery.SetSafeDestination(exitPoint);
        recovery.EnterSeat();
    }

    public override void OnStationExited(VRCPlayerApi player)
    {
        if (!Utilities.IsValid(player) || !player.isLocal || recovery == null) return;
        recovery.ExitSeat();
    }
}
