import React, { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000/api";

export default function App() {
  const [events, setEvents] = useState([]);
  const [pattern, setPattern] = useState(null);
  const [workflow, setWorkflow] = useState(null);
  const [execution, setExecution] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

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
            {loading ? "PROCESSING..." : "▶ RUN DEMO"}
          </button>
        </section>

        {message && <div className="message">{message}</div>}

        {/* PIPELINE */}
        <section className="pipeline">
          <div className="pipeline-step active">
            <span>01</span>
            Observe
          </div>
          <div className="arrow">→</div>
          <div className="pipeline-step active">
            <span>02</span>
            Detect
          </div>
          <div className="arrow">→</div>
          <div className="pipeline-step active">
            <span>03</span>
            Understand
          </div>
          <div className="arrow">→</div>
          <div className="pipeline-step active">
            <span>04</span>
            Generate
          </div>
          <div className="arrow">→</div>
          <div className="pipeline-step active">
            <span>05</span>
            Automate
          </div>
        </section>

        {/* ACTIVITY */}
        <section className="card">
          <div className="section-header">
            <div>
              <p className="section-label">LIVE ACTIVITY</p>
              <h2>Observed Work Pattern</h2>
            </div>

            {events.length > 0 && (
              <span className="pill">{events.length} EVENTS</span>
            )}
          </div>

          <div className="activity-flow">
            {[
              ["Gmail", "Open Email", "✉"],
              ["Browser Download", "Download File", "↓"],
              ["HubSpot CRM", "Update Customer", "◆"],
              ["Slack", "Send Message", "●"],
            ].map(([app, action, icon], index) => (
              <React.Fragment key={app}>
                <div className="activity-item">
                  <div className="activity-icon">{icon}</div>
                  <div>
                    <strong>{app}</strong>
                    <small>{action}</small>
                  </div>
                </div>

                {index < 3 && <div className="flow-arrow">→</div>}
              </React.Fragment>
            ))}
          </div>
        </section>

        {/* DETECTION */}
        {pattern && (
          <section className="card detection-card">
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
          <section className="card workflow-card">
            <div className="section-header">
              <div>
                <p className="section-label">AI-GENERATED WORKFLOW</p>
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

            <div className="workflow-footer">
              <div className="time-saving">
                <span>⚡</span>
                <div>
                  <strong>
                    {workflow.estimated_time_saved_minutes} min
                  </strong>
                  <small>estimated time saved</small>
                </div>
              </div>

              {workflow.status === "PENDING_APPROVAL" && (
                <button className="approve-button" onClick={approveWorkflow}>
                  ✓ APPROVE & AUTOMATE
                </button>
              )}

              {workflow.status === "APPROVED" && (
                <button className="approve-button" onClick={executeWorkflow}>
                  ▶ EXECUTE WORKFLOW
                </button>
              )}
            </div>
          </section>
        )}

        {/* EXECUTION */}
        {execution && (
          <section className="card execution-card">
            <div className="section-header">
              <div>
                <p className="section-label">AUTOMATION RESULT</p>
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

        <footer>
          <span>WorkFlowOS • Hackathon MVP</span>
          <span>Observe → Understand → Automate</span>
        </footer>
      </main>
    </div>
  );
}