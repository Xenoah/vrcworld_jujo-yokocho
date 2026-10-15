using UdonSharp;
using UnityEngine;

// A physical sign/button, not shared UI state. Target events are local-only APIs.
[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class YokochoEntryControl : UdonSharpBehaviour
{
    public UdonSharpBehaviour target;
    public string eventName;
    [Range(0.2f, 2f)] public float cooldownSeconds = 0.4f;
    private float nextUse;

    public override void Interact()
    {
        if (target == null || string.IsNullOrEmpty(eventName) || Time.time < nextUse) return;
        // Only local-only controller APIs can be wired by this component.
        if (!eventName.StartsWith("_")) return;
        nextUse = Time.time + Mathf.Max(0.2f, cooldownSeconds);
        target.SendCustomEvent(eventName);
    }
}
