import React, { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000/api";

const PHASES = [
  { id: 1, label: "Observe" },
  { id: 2, label: "Understand" },
  { id: 3, label: "Detect Repetition" },
  { id: 4, label: "Generate Workflow" },
  { id: 5, label: "User Approval" },
  { id: 6, label: "Automate" },
  { id: 7, label: "Learn" },
];

function getAppInfo(rawApp = "") {
  const lower = rawApp.toLowerCase();
  if (lower.includes("gmail") || lower.includes("mail")) {
    return { name: "Gmail", icon: "✉", color: "#f87171", bg: "rgba(239, 68, 68, 0.14)" };
  }
  if (lower.includes("download") || lower.includes("browser")) {
    return { name: "Browser Download", icon: "↓", color: "#38bdf8", bg: "rgba(56, 189, 248, 0.14)" };
  }
  if (lower.includes("hubspot") || lower.includes("crm")) {
    return { name: "HubSpot CRM", icon: "◆", color: "#fb923c", bg: "rgba(251, 146, 60, 0.14)" };
  }
  if (lower.includes("slack")) {
    return { name: "Slack", icon: "●", color: "#f472b6", bg: "rgba(244, 114, 182, 0.14)" };
  }
  return { name: rawApp || "App", icon: "❖", color: "#94a3b8", bg: "rgba(148, 163, 184, 0.14)" };
}

function formatAction(action = "") {
  return action
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatTime(isoString) {
  if (!isoString) return "";
  try {
    const date = new Date(isoString);
    if (!isNaN(date.getTime())) {
      return date.toLocaleTimeString([], { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
    }
  } catch (_) { }
  return (isoString || "").slice(11, 19);
}

function getEventDescription(event) {
  const meta = event.metadata || {};
  if (event.action === "open_email") {
    const subject = meta.subject || "";
    const sender = meta.sender ? `from ${meta.sender}` : "";
    return subject ? `${subject} (${sender})` : event.window_title || "Email opened";
  }
  if (event.action === "download_file") {
    const file = meta.file_name || "attachment";
    return `Saved file: ${file}`;
  }
  if (event.action === "update_customer_record") {
    const customer = meta.customer_name ? `${meta.customer_name} (ID: ${meta.customer_id})` : "";
    const update = meta.field_updated ? `set ${meta.field_updated} = ${meta.value}` : "Record updated";
    return customer ? `${customer} — ${update}` : update;
  }
  if (event.action === "send_message") {
    const ch = meta.channel ? `${meta.channel}: ` : "";
    const msg = meta.message || "Message sent";
    return `${ch}"${msg}"`;
  }
  return event.window_title || event.action;
}

export default function App() {
  const [events, setEvents] = useState([]);
  const [pattern, setPattern] = useState(null);
  const [workflow, setWorkflow] = useState(null);
  const [execution, setExecution] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [activePhase, setActivePhase] = useState(1);

  async function loadDemo() {
    setLoading(true);
    setMessage("");

    try {
      // 1. Load activity + detect repetition
      const detectRes = await fetch(
        `${API}/workflows/detect?auto_load_demo=true`
      );
      const detected = await detectRes.json();

      if (detected.length > 0) {
        setPattern(detected[0]);

        // 2. Get the demo events
        const eventsRes = await fetch(`${API}/events`);
        setEvents(await eventsRes.json());

        // 3. Generate workflow
        const workflowRes = await fetch(`${API}/workflows/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(detected[0]),
        });

        setWorkflow(await workflowRes.json());
      }
    } catch (error) {
      console.error(error);
      setMessage("Could not connect to WorkFlowOS backend.");
    } finally {
      setLoading(false);
    }
  }

  async function approveWorkflow() {
    if (!workflow) return;

    try {
      const res = await fetch(
        `${API}/workflows/${workflow.workflow_id}/approve`,
        { method: "POST" }
      );

      const approved = await res.json();
      setWorkflow(approved);
      setMessage("Workflow approved. Ready to automate.");
    } catch (error) {
      setMessage("Approval failed.");
    }
  }

  async function rejectWorkflow() {
    if (!workflow) return;

    try {
      const res = await fetch(
        `${API}/workflows/${workflow.workflow_id}/reject`,
        { method: "POST" }
      );

      const rejected = await res.json();
      setWorkflow(rejected);
      setMessage("Workflow rejected. No automation executed.");
    } catch (error) {
      setMessage("Rejection failed.");
    }
  }


  async function executeWorkflow() {
    if (!workflow) return;

    setLoading(true);
    setMessage("");

    try {
      const res = await fetch(
        `${API}/execution/run/${workflow.workflow_id}`,
        { method: "POST" }
      );

      const result = await res.json();
      setExecution(result);
      setMessage("Automation completed successfully.");
    } catch (error) {
      setMessage("Execution failed.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDemo();
  }, []);

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <div className="brand">
            <span className="brand-mark">W</span>
            <span>WorkFlowOS</span>
          </div>
          <p className="tagline">
            AI-powered workflow automation that learns from repetitive work
          </p>
        </div>

        <div className="status">
          <span className="status-dot"></span>
          SYSTEM ONLINE
        </div>
      </header>

      <main className="container">
        <section className="hero">
          <div>
            <p className="eyebrow">AUTOMATION INTELLIGENCE</p>
            <h1>
              Your repetitive work,
              <br />
              <span>automated automatically.</span>
            </h1>
            <p className="hero-text">
              WorkFlowOS observes activity, detects repeated workflows,
              understands the user's intent, and turns them into approved
              automations.
            </p>
          </div>

          <button className="demo-button" onClick={loadDemo} disabled={loading}>
            {loading ? "PROCESSING..." : "↻ REPLAY DEMO"}
          </button>
        </section>

        {message && <div className="message">{message}</div>}

        {/* PIPELINE / 7-PHASE LIFECYCLE */}
        <section className="pipeline">
          {PHASES.map((phase, index) => {
            const isActive = activePhase === phase.id;
            const isCompleted = activePhase > phase.id;

            return (
              <React.Fragment key={phase.id}>
                <button
                  type="button"
                  className={`pipeline-step ${isActive ? "active" : ""} ${isCompleted ? "completed" : ""}`}
                  onClick={() => {
                    setActivePhase(phase.id);
                    const targets = {
                      1: "phase-observe",
                      2: "phase-understand",
                      3: "phase-detect",
                      4: "phase-generate",
                      5: "phase-approval",
                      6: "phase-automate",
                      7: "phase-learn",
                    };
                    document.getElementById(targets[phase.id])?.scrollIntoView({
                      behavior: "smooth",
                      block: "start",
                    });
                  }}
                >
                  <span className="step-num">
                    {isCompleted ? "✓" : `0${phase.id}`}
                  </span>
                  <span className="step-label">{phase.label}</span>
                </button>
                {index < PHASES.length - 1 && (
                  <div className={`arrow ${isCompleted ? "completed" : ""}`}>
                    →
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </section>

        {/* PHASE 1: OBSERVE */}
        <section id="phase-observe" className="card observe-card">
          <div className="section-header">
            <div>
              <p className="section-label">PHASE 01 • OBSERVE</p>
              <h2>Demo Observation Mode • Structured Activity Stream</h2>
            </div>

            {events.length > 0 && (
              <span className="pill">{events.length} OBSERVED EVENTS</span>
            )}
          </div>

          {/* VISUAL SEQUENCE BAR */}
          <div className="sequence-banner">
            <span className="sequence-tag">OBSERVED SEQUENCE</span>
            <div className="sequence-steps">
              <span className="sequence-chip gmail">Gmail</span>
              <span className="sequence-arrow">→</span>
              <span className="sequence-chip download">Browser Download</span>
              <span className="sequence-arrow">→</span>
              <span className="sequence-chip crm">HubSpot CRM</span>
              <span className="sequence-arrow">→</span>
              <span className="sequence-chip slack">Slack</span>
            </div>
          </div>

          {/* CHRONOLOGICAL ACTIVITY STREAM */}
          <div className="activity-stream">
            {events.length === 0 ? (
              <div className="activity-empty">
                Listening for desktop activity... Click "RUN DEMO" to ingest activity stream.
              </div>
            ) : (
              events.map((event, index) => {
                const appInfo = getAppInfo(event.app);
                const actionLabel = formatAction(event.action);
                const desc = getEventDescription(event);
                const timeStr = formatTime(event.timestamp);
                const isCycleStart = index > 0 && index % 4 === 0;

                return (
                  <React.Fragment key={event.event_id || index}>
                    {isCycleStart && (
                      <div className="cycle-divider">
                        <span>Cycle {Math.floor(index / 4) + 1}</span>
                      </div>
                    )}
                    <div className="stream-item">
                      <div className="stream-time">{timeStr}</div>

                      <div
                        className="stream-app-badge"
                        style={{ color: appInfo.color, background: appInfo.bg }}
                      >
                        <span className="stream-app-icon">{appInfo.icon}</span>
                        <span>{appInfo.name}</span>
                      </div>

                      <div className="stream-action">{actionLabel}</div>

                      <div className="stream-desc" title={desc}>
                        {desc}
                      </div>

                      <div className="stream-step-tag">
                        Step {(index % 4) + 1}/4
                      </div>
                    </div>
                  </React.Fragment>
                );
              })
            )}
          </div>
        </section>

        {/* PHASE 02: UNDERSTAND */}
        {workflow && (
          <section id="phase-understand" className="card understand-card">
            <div className="section-header">
              <div>
                <p className="section-label">PHASE 02 • UNDERSTAND</p>
                <h2>AI Understanding</h2>
              </div>
              <span className="status-pill approved">AI INTERPRETED</span>
            </div>

            <div className="understand-content">
              <div className="understand-main">
                <span className="understand-label">IDENTIFIED INTENT</span>
                <h3>{workflow.name}</h3>
                <p>{workflow.intent_summary}</p>
              </div>

              <div className="understand-flow">
                <div>
                  <strong>Observed Activity</strong>
                  <span>{events.length} events</span>
                </div>
                <span className="understand-arrow">→</span>
                <div>
                  <strong>AI Interpretation</strong>
                  <span>Workflow intent identified</span>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* DETECTION */}
        {pattern && (
          <section id="phase-detect" className="card detection-card">
            <div className="detection-badge">↻ REPETITION DETECTED</div>

            <div className="metrics">
              <div>
                <strong>{pattern.occurrence_count}</strong>
                <span>Occurrences</span>
              </div>

              <div>
                <strong>
                  {Math.round(pattern.confidence_score * 100)}%
                </strong>
                <span>Confidence</span>
              </div>

              <div>
                <strong>4</strong>
                <span>Applications</span>
              </div>
            </div>

            <p className="pattern-description">{pattern.description}</p>
          </section>
        )}

        {/* WORKFLOW */}
        {workflow && (
          <section id="phase-generate" className="card workflow-card">
            <div className="section-header">
              <div>
                <p className="section-label">PHASE 04 • GENERATE WORKFLOW</p>
                <h2>{workflow.name}</h2>
              </div>

              <span className={`status-pill ${workflow.status.toLowerCase()}`}>
                {workflow.status.replace("_", " ")}
              </span>
            </div>

            <p className="intent">{workflow.intent_summary}</p>

            <div className="trigger">
              <span className="trigger-label">TRIGGER</span>
              <span>{workflow.trigger_description}</span>
            </div>

            <div className="workflow-steps">
              {workflow.steps.map((step) => (
                <div className="workflow-step" key={step.step_id}>
                  <div className="step-number">{step.step_order}</div>

                  <div className="step-content">
                    <strong>{step.title}</strong>
                    <p>{step.description}</p>
                  </div>

                  <div className="step-app">{step.app}</div>
                </div>
              ))}
            </div>

            <div id="phase-approval" className="workflow-footer">
              <div className="time-saving">
                <span>⚡</span>
                <div>
                  <strong>
                    {workflow.estimated_time_saved_minutes} min
                  </strong>
                  <small>estimated time saved</small>
                </div>
              </div>

              <div className="approval-summary">
                <span className="approval-label">PHASE 05 • USER APPROVAL</span>
                <strong>Review before automation</strong>
                <small>
                  WorkFlowOS will execute these steps only after human approval.
                </small>
              </div>

              <div className="approval-actions">
                {workflow.status === "PENDING_APPROVAL" && (
                  <>
                    <button
                      className="reject-button"
                      onClick={rejectWorkflow}
                    >
                      ✕ REJECT
                    </button>

                    <button
                      className="approve-button"
                      onClick={approveWorkflow}
                    >
                      ✓ APPROVE & AUTOMATE
                    </button>
                  </>
                )}

                {workflow.status === "APPROVED" && (
                  <button className="approve-button" onClick={executeWorkflow}>
                    ▶ EXECUTE WORKFLOW
                  </button>
                )}
              </div>
            </div>
          </section>
        )}

        {/* EXECUTION */}
        {execution && (
          <section id="phase-automate" className="card execution-card">
            <div className="section-header">
              <div>
                <p className="section-label">PHASE 06 • AUTOMATE</p>
                <h2>Workflow Executed</h2>
              </div>

              <span className="success-pill">✓ SUCCESS</span>
            </div>

            <div className="execution-summary">
              <div>
                <strong>{execution.total_duration_ms} ms</strong>
                <span>Execution Time</span>
              </div>

              <div>
                <strong>
                  {execution.step_results.filter(
                    (s) => s.status === "SUCCESS"
                  ).length}
                  /{execution.step_results.length}
                </strong>
                <span>Steps Completed</span>
              </div>

              <div>
                <strong>{execution.estimated_time_saved_minutes} min</strong>
                <span>Time Saved</span>
              </div>
            </div>

            <div className="execution-steps">
              {execution.step_results.map((step) => (
                <div className="execution-step" key={step.step_id}>
                  <span className="check">✓</span>

                  <div>
                    <strong>{step.step_title}</strong>
                    <small>{step.output_summary}</small>
                  </div>

                  <span className="duration">
                    {step.duration_ms} ms
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}
        <section id="phase-learn" className="learn-card">
          <div className="section-header">
            <div>
              <p className="section-label">PHASE 07 • LEARN</p>
              <h2>Learning Signal Recorded</h2>
            </div>
            <span className="success-pill">✓ RECORDED</span>
          </div>

          <div className="learn-grid">
            <div>
              <strong>1</strong>
              <span>Successful run</span>
            </div>

            <div>
              <strong>4/4</strong>
              <span>Steps completed</span>
            </div>

            <div>
              <strong>3 min</strong>
              <span>Time saved</span>
            </div>
          </div>

          <p className="learn-description">
            WorkFlowOS records execution history so future workflow suggestions
            can be refined from successful runs.
          </p>
        </section>

        <footer>
          <span>WorkFlowOS • Hackathon MVP</span>
          <span>Observe → Understand → Detect → Generate → Approve → Automate → Learn</span>
        </footer>
      </main>
    </div>
  );
}