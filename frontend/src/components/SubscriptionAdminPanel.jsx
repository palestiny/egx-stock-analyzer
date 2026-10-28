import { useState } from "react";

const DEFAULT_ENTITLEMENTS = '[{"code":"telegram_opportunities","enabled":true,"limit":50}]';

function asPrettyJson(value) {
  return JSON.stringify(value, null, 2);
}

export function SubscriptionAdminPanel({
  createPlan,
  createSubscription,
  getSubscription,
  getLatestSubscriptionByUser,
  transitionSubscription,
}) {
  const [planId, setPlanId] = useState("telegram-pilot");
  const [planVersion, setPlanVersion] = useState("1");
  const [planName, setPlanName] = useState("Telegram Pilot");
  const [entitlementsJson, setEntitlementsJson] = useState(DEFAULT_ENTITLEMENTS);
  const [planActive, setPlanActive] = useState(true);
  const [userId, setUserId] = useState("");
  const [subscriptionPlanId, setSubscriptionPlanId] = useState("telegram-pilot");
  const [subscriptionPlanVersion, setSubscriptionPlanVersion] = useState("1");
  const [startsAt, setStartsAt] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [provisionReason, setProvisionReason] = useState("");
  const [paymentProvider, setPaymentProvider] = useState("");
  const [paymentReference, setPaymentReference] = useState("");
  const [subscriptionId, setSubscriptionId] = useState("");
  const [lookupUserId, setLookupUserId] = useState("");
  const [currentSubscription, setCurrentSubscription] = useState(null);
  const [nextStatus, setNextStatus] = useState("ACTIVE");
  const [transitionReason, setTransitionReason] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busyAction, setBusyAction] = useState(null);

  async function runAction(action, operation) {
    setBusyAction(action);
    setError(null);
    setResult(null);
    try {
      const value = await operation();
      setResult({ action, value });
      if (value?.subscription_id) setCurrentSubscription(value);
      return value;
    } catch (requestError) {
      setError(requestError?.message || "Request failed");
      return null;
    } finally {
      setBusyAction(null);
    }
  }

  async function handleCreatePlan(event) {
    event.preventDefault();
    let entitlements;
    try {
      entitlements = JSON.parse(entitlementsJson);
      if (!Array.isArray(entitlements)) throw new Error("Entitlements must be a JSON array");
    } catch (parseError) {
      setError(parseError instanceof SyntaxError
        ? "Entitlements must be valid JSON"
        : parseError.message || "Entitlements must be a JSON array");
      return;
    }
    await runAction("plan", () => createPlan({
      plan_id: planId.trim(),
      version: Number(planVersion),
      display_name: planName.trim(),
      entitlements,
      active: planActive,
    }));
  }

  async function handleCreateSubscription(event) {
    event.preventDefault();
    const payload = {
      user_id: userId.trim(),
      plan_id: subscriptionPlanId.trim(),
      plan_version: Number(subscriptionPlanVersion),
      starts_at: startsAt.trim(),
      expires_at: expiresAt.trim(),
      reason: provisionReason.trim(),
      payment_provider: paymentProvider.trim() || null,
      payment_reference: paymentReference.trim() || null,
    };
    const value = await runAction("subscription", () => createSubscription(payload));
    if (value?.subscription_id) {
      setSubscriptionId(value.subscription_id);
      setCurrentSubscription(value);
    }
  }

  async function handleLookupById(event) {
    event.preventDefault();
    const value = await runAction("lookup", () => getSubscription(subscriptionId.trim()));
    if (value?.subscription_id) setCurrentSubscription(value);
  }

  async function handleLookupByUser(event) {
    event.preventDefault();
    const value = await runAction("lookup", () => getLatestSubscriptionByUser(lookupUserId.trim()));
    if (value?.subscription_id) {
      setCurrentSubscription(value);
      setSubscriptionId(value.subscription_id);
    }
  }

  async function handleTransition(event) {
    event.preventDefault();
    if (!currentSubscription?.subscription_id) return;
    const value = await runAction("transition", () =>
      transitionSubscription(currentSubscription.subscription_id, {
        status: nextStatus,
        reason: transitionReason.trim(),
      }),
    );
    if (value?.subscription_id) setCurrentSubscription(value);
  }

  return (
    <section className="panel" aria-label="subscription administration">
      <h2>Subscription administration</h2>
      <p className="muted">
        Operator-only manual administration. New subscriptions start as PENDING. Activation must be an explicit audited transition.
        This panel does not process payments, set prices, or prove that payment was received.
      </p>

      <form className="owner-admin-form" onSubmit={handleCreatePlan}>
        <h3>Create immutable plan version</h3>
        <label>
          Plan ID
          <input value={planId} onChange={(event) => setPlanId(event.target.value)} required />
        </label>
        <label>
          Version
          <input type="number" min="1" value={planVersion} onChange={(event) => setPlanVersion(event.target.value)} required />
        </label>
        <label>
          Display name
          <input value={planName} onChange={(event) => setPlanName(event.target.value)} required />
        </label>
        <label>
          Entitlements JSON
          <textarea rows="4" value={entitlementsJson} onChange={(event) => setEntitlementsJson(event.target.value)} required />
        </label>
        <label className="checkbox-row">
          <input type="checkbox" checked={planActive} onChange={(event) => setPlanActive(event.target.checked)} />
          Active plan version
        </label>
        <button type="submit" disabled={busyAction !== null || !createPlan}>
          {busyAction === "plan" ? "Saving plan..." : "Create plan version"}
        </button>
      </form>

      <form className="owner-admin-form" onSubmit={handleCreateSubscription}>
        <h3>Provision pending subscription</h3>
        <label>
          User ID
          <input value={userId} onChange={(event) => setUserId(event.target.value)} required placeholder="UUID" />
        </label>
        <label>
          Plan ID
          <input value={subscriptionPlanId} onChange={(event) => setSubscriptionPlanId(event.target.value)} required />
        </label>
        <label>
          Plan version
          <input type="number" min="1" value={subscriptionPlanVersion} onChange={(event) => setSubscriptionPlanVersion(event.target.value)} required />
        </label>
        <label>
          Starts at (ISO-8601 with timezone)
          <input value={startsAt} onChange={(event) => setStartsAt(event.target.value)} required placeholder="2026-10-28T09:00:00+03:00" />
        </label>
        <label>
          Expires at (ISO-8601 with timezone)
          <input value={expiresAt} onChange={(event) => setExpiresAt(event.target.value)} required placeholder="2026-11-28T09:00:00+03:00" />
        </label>
        <label>
          Audit reason
          <input value={provisionReason} onChange={(event) => setProvisionReason(event.target.value)} required />
        </label>
        <label>
          Payment provider (optional reference only)
          <input value={paymentProvider} onChange={(event) => setPaymentProvider(event.target.value)} />
        </label>
        <label>
          Payment reference (optional; does not verify payment)
          <input value={paymentReference} onChange={(event) => setPaymentReference(event.target.value)} />
        </label>
        <button type="submit" disabled={busyAction !== null || !createSubscription}>
          {busyAction === "subscription" ? "Provisioning..." : "Create pending subscription"}
        </button>
      </form>

      <form className="owner-admin-form" onSubmit={handleLookupById}>
        <h3>Inspect subscription</h3>
        <label>
          Subscription ID
          <input value={subscriptionId} onChange={(event) => setSubscriptionId(event.target.value)} placeholder="UUID" />
        </label>
        <button type="submit" disabled={busyAction !== null || !subscriptionId.trim() || !getSubscription}>
          Find by subscription ID
        </button>
      </form>

      <form className="owner-admin-form" onSubmit={handleLookupByUser}>
        <label>
          User ID for latest subscription
          <input value={lookupUserId} onChange={(event) => setLookupUserId(event.target.value)} placeholder="UUID" />
        </label>
        <button type="submit" disabled={busyAction !== null || !lookupUserId.trim() || !getLatestSubscriptionByUser}>
          Find latest by user
        </button>
      </form>

      {currentSubscription?.subscription_id && (
        <form className="owner-admin-form" onSubmit={handleTransition}>
          <h3>Transition subscription status</h3>
          <p className="muted">Current status: {currentSubscription.status}</p>
          <label>
            New status
            <select value={nextStatus} onChange={(event) => setNextStatus(event.target.value)}>
              {["PENDING", "ACTIVE", "PAST_DUE", "CANCELLED", "EXPIRED", "REFUNDED"].map((status) => (
                <option key={status} value={status}>{status}</option>
              ))}
            </select>
          </label>
          <label>
            Audit reason
            <input value={transitionReason} onChange={(event) => setTransitionReason(event.target.value)} required />
          </label>
          <button type="submit" disabled={busyAction !== null || !transitionSubscription}>
            {busyAction === "transition" ? "Saving status..." : "Record status transition"}
          </button>
        </form>
      )}

      {error && <p className="state-card error" role="alert">{error}</p>}
      {result && (
        <section aria-label="subscription administration result">
          <h3>Latest result: {result.action}</h3>
          <pre className="json-result">{asPrettyJson(result.value)}</pre>
        </section>
      )}
    </section>
  );
}
