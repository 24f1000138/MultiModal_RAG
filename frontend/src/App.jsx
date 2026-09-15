import { useState, useRef, useEffect, useCallback } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

const API_BASE = "http://localhost:8000";

const api = {
  ingestDocument: (formData) =>
    fetch(`${API_BASE}/ingest`, { method: "POST", body: formData }).then((r) => r.json()),
  searchDocuments: (keyword) =>
    fetch(`${API_BASE}/search?q=${encodeURIComponent(keyword)}`).then((r) => r.json()),
  retrieveDocument: (query, docs) =>
    fetch(`${API_BASE}/retrieve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, documents: docs, mode: "specific" }),
    }).then((r) => r.json()),
  retrieveAll: (query) =>
    fetch(`${API_BASE}/retrieve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, mode: "all" }),
    }).then((r) => r.json()),
  getEvaluation: (evaluationId) =>
    fetch(`${API_BASE}/evaluation/${evaluationId}`).then((r) => r.json()),
};

function useTypewriter(text, speed = 18) {
  const [displayed, setDisplayed] = useState("");
  const [done, setDone] = useState(false);
  useEffect(() => {
    if (!text) return;
    setDisplayed("");
    setDone(false);
    let i = 0;
    const iv = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) { clearInterval(iv); setDone(true); }
    }, speed);
    return () => clearInterval(iv);
  }, [text, speed]);
  return { displayed, done };
}

function GlowOrb({ style }) {
  return (
    <div style={{
      position: "absolute",
      borderRadius: "50%",
      filter: "blur(80px)",
      pointerEvents: "none",
      ...style,
    }} />
  );
}

function GridPattern() {
  return (
    <svg
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.04, pointerEvents: "none" }}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="white" strokeWidth="0.5" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#grid)" />
    </svg>
  );
}

function Badge({ children, color = "#6366f1" }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: "2px 10px", borderRadius: 100,
      fontSize: 11, fontWeight: 600, letterSpacing: "0.06em",
      background: color + "22", color,
      border: `1px solid ${color}44`,
    }}>
      {children}
    </span>
  );
}

function GlassCard({ children, style, glow }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.04)",
      border: "1px solid rgba(255,255,255,0.1)",
      borderRadius: 16,
      backdropFilter: "blur(12px)",
      boxShadow: glow ? `0 0 40px ${glow}22, inset 0 1px 0 rgba(255,255,255,0.1)` : "inset 0 1px 0 rgba(255,255,255,0.06)",
      ...style,
    }}>
      {children}
    </div>
  );
}

function PulsingDot({ color = "#6366f1" }) {
  return (
    <span style={{ position: "relative", display: "inline-flex", width: 10, height: 10 }}>
      <span style={{
        position: "absolute", inset: 0, borderRadius: "50%",
        background: color, opacity: 0.4,
        animation: "ping 1.2s cubic-bezier(0,0,0.2,1) infinite",
      }} />
      <span style={{ width: 10, height: 10, borderRadius: "50%", background: color, display: "block" }} />
    </span>
  );
}

function Spinner() {
  return (
    <div style={{
      width: 20, height: 20, borderRadius: "50%",
      border: "2px solid rgba(99,102,241,0.2)",
      borderTopColor: "#6366f1",
      animation: "spin 0.8s linear infinite",
      display: "inline-block",
    }} />
  );
}

function AnimatedInput({ value, onChange, placeholder, onEnter, icon }) {
  const [focused, setFocused] = useState(false);
  return (
    <div style={{
      position: "relative",
      border: `1px solid ${focused ? "rgba(99,102,241,0.6)" : "rgba(255,255,255,0.1)"}`,
      borderRadius: 12,
      background: "rgba(255,255,255,0.04)",
      backdropFilter: "blur(8px)",
      transition: "border-color 0.2s, box-shadow 0.2s",
      boxShadow: focused ? "0 0 0 3px rgba(99,102,241,0.15)" : "none",
      display: "flex", alignItems: "center",
    }}>
      {icon && (
        <span style={{ paddingLeft: 14, color: "rgba(255,255,255,0.3)", fontSize: 18 }}>{icon}</span>
      )}
      <input
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        onKeyDown={e => e.key === "Enter" && onEnter?.()}
        style={{
          flex: 1, background: "transparent", border: "none", outline: "none",
          color: "#fff", fontSize: 15, padding: "12px 14px",
          fontFamily: "inherit",
        }}
      />
    </div>
  );
}

function GlowButton({ children, onClick, disabled, variant = "primary", style }) {
  const [hovered, setHovered] = useState(false);
  const colors = {
    primary: { bg: "#6366f1", glow: "#6366f1", text: "#fff" },
    ghost: { bg: "rgba(255,255,255,0.06)", glow: "rgba(255,255,255,0.1)", text: "rgba(255,255,255,0.7)" },
    danger: { bg: "#ef4444", glow: "#ef4444", text: "#fff" },
  };
  const c = colors[variant];
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8,
        padding: "10px 20px", borderRadius: 10, border: "none", cursor: disabled ? "not-allowed" : "pointer",
        background: hovered && !disabled ? c.bg : variant === "primary" ? c.bg + "cc" : c.bg,
        color: c.text, fontSize: 14, fontWeight: 600, fontFamily: "inherit",
        boxShadow: hovered && !disabled ? `0 0 20px ${c.glow}66` : "none",
        transition: "all 0.2s",
        opacity: disabled ? 0.5 : 1,
        ...style,
      }}
    >
      {children}
    </button>
  );
}

function FileDropzone({ onFile, file }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef();

  const handleDrop = (e) => {
    e.preventDefault(); setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f?.type === "application/pdf") onFile(f);
  };

  return (
    <div
      onClick={() => inputRef.current.click()}
      onDragOver={e => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      style={{
        border: `1.5px dashed ${dragging ? "#6366f1" : "rgba(255,255,255,0.15)"}`,
        borderRadius: 14,
        padding: "28px 20px",
        textAlign: "center", cursor: "pointer",
        background: dragging ? "rgba(99,102,241,0.08)" : "rgba(255,255,255,0.02)",
        transition: "all 0.2s",
      }}
    >
      <input ref={inputRef} type="file" accept=".pdf" onChange={e => onFile(e.target.files[0])} style={{ display: "none" }} />
      <div style={{ fontSize: 32, marginBottom: 10 }}>📄</div>
      {file ? (
        <div>
          <div style={{ color: "#a5b4fc", fontWeight: 600, fontSize: 14 }}>{file.name}</div>
          <div style={{ color: "rgba(255,255,255,0.4)", fontSize: 12, marginTop: 4 }}>
            {(file.size / 1024).toFixed(1)} KB · Click to replace
          </div>
        </div>
      ) : (
        <div>
          <div style={{ color: "rgba(255,255,255,0.7)", fontSize: 14, fontWeight: 500 }}>Drop PDF here or click to browse</div>
          <div style={{ color: "rgba(255,255,255,0.3)", fontSize: 12, marginTop: 4 }}>Supports PDF files</div>
        </div>
      )}
    </div>
  );
}

function SectionLabel({ children }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 10, marginBottom: 14,
    }}>
      <div style={{ width: 3, height: 16, borderRadius: 2, background: "#6366f1" }} />
      <span style={{ color: "rgba(255,255,255,0.5)", fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase" }}>
        {children}
      </span>
    </div>
  );
}

function AnswerCard({ answer }) {
  const { displayed } = useTypewriter(answer, 12);
  return (
    <GlassCard glow="#6366f1" style={{ padding: 24 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          background: "linear-gradient(135deg,#6366f1,#8b5cf6)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 16,
        }}>✦</div>
        <span style={{ color: "rgba(255,255,255,0.9)", fontWeight: 600, fontSize: 15 }}>Answer</span>
        <PulsingDot color="#6366f1" />
      </div>
      <div style={{ color: "rgba(255,255,255,0.82)", fontSize: 15, lineHeight: 1.75, whiteSpace: "pre-wrap" }}>
        {displayed}
        <span style={{ opacity: 0.4, animation: "blink 1s step-end infinite" }}>|</span>
      </div>
    </GlassCard>
  );
}

function EvaluationCard({ evaluation, status }) {
  if (status === "pending") {
    return (
      <GlassCard style={{ padding: 20 }}>
        <SectionLabel>Answer Evaluation</SectionLabel>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            color: "rgba(255,255,255,0.6)",
            fontSize: 14,
          }}
        >
          <Spinner />
          Evaluating generated answer…
        </div>
      </GlassCard>
    );
  }

  if (status === "failed") {
    return (
      <GlassCard style={{ padding: 20 }}>
        <SectionLabel>Answer Evaluation</SectionLabel>
        <p style={{ color: "#f87171", fontSize: 14 }}>
          Evaluation failed.
        </p>
      </GlassCard>
    );
  }

  if (status !== "completed" || !evaluation) {
    return null;
  }

  const criteria = [
    {
      name: "Context Relevance",
      data: evaluation.context_relevance,
    },
    {
      name: "Faithfulness",
      data: evaluation.faithfulness,
    },
    {
      name: "Answer Relevance",
      data: evaluation.answer_relevance,
    },
    {
      name: "Answer Completeness",
      data: evaluation.answer_completeness,
    },
  ];

  return (
    <GlassCard glow="#0ea5e9" style={{ padding: 24 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          marginBottom: 20,
        }}
      >
        <SectionLabel>Answer Evaluation</SectionLabel>

        <Badge color="#0ea5e9">LLM Evaluation</Badge>
      </div>

      <div
        style={{
          padding: 16,
          borderRadius: 12,
          background: "rgba(14,165,233,0.1)",
          border: "1px solid rgba(14,165,233,0.25)",
          marginBottom: 20,
        }}
      >
        <div
          style={{
            color: "rgba(255,255,255,0.5)",
            fontSize: 12,
            marginBottom: 6,
          }}
        >
          Overall Answer Quality
        </div>

        <div
          style={{
            fontSize: 32,
            fontWeight: 700,
            color: "#7dd3fc",
          }}
        >
          {evaluation.answer_quality?.overall_score ?? "N/A"} / 5
        </div>

        <div
          style={{
            color: "rgba(255,255,255,0.7)",
            fontSize: 13,
            lineHeight: 1.6,
            marginTop: 8,
          }}
        >
          {evaluation.answer_quality?.reason}
        </div>
      </div>

      {criteria.map((criterion) => (
        <div
          key={criterion.name}
          style={{
            padding: "14px 0",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: 12,
              marginBottom: 6,
            }}
          >
            <strong style={{ fontSize: 14 }}>
              {criterion.name}
            </strong>

            <Badge color="#a5b4fc">
              {criterion.data?.score ?? "N/A"} / 5
            </Badge>
          </div>

          <div
            style={{
              color: "rgba(255,255,255,0.6)",
              fontSize: 13,
              lineHeight: 1.6,
            }}
          >
            {criterion.data?.reason || "No reason provided."}
          </div>
        </div>
      ))}

      <div style={{ marginTop: 20 }}>
        <h3 style={{ fontSize: 14, marginBottom: 10 }}>
          Unsupported Claims
        </h3>

        {!evaluation.unsupported_claims ||
        evaluation.unsupported_claims.length === 0 ? (
          <div
            style={{
              color: "#86efac",
              fontSize: 13,
            }}
          >
            ✓ No unsupported claims detected.
          </div>
        ) : (
          <ul
            style={{
              color: "rgba(255,255,255,0.7)",
              fontSize: 13,
              lineHeight: 1.6,
              paddingLeft: 20,
            }}
          >
            {evaluation.unsupported_claims.map((claim, index) => (
              <li key={index}>
                {typeof claim === "string"
                  ? claim
                  : JSON.stringify(claim)}
              </li>
            ))}
          </ul>
        )}
      </div>
    </GlassCard>
  );
}

function ChunkCard({ chunk, content, index, onOpenPDF }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <GlassCard style={{ padding: 18, marginBottom: 10 }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 10 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
            <Badge color="#6366f1">Chunk {index}</Badge>
            <Badge color="#0ea5e9">{chunk.chunk_type}</Badge>
            {chunk.metadata_json?.section && <Badge color="#8b5cf6">{chunk.metadata_json.section}</Badge>}
          </div>
          <div style={{ color: "rgba(255,255,255,0.5)", fontSize: 12, marginBottom: 8 }}>
            📁 {chunk.source_file?.split("/").pop()} · Page {chunk.page_number}
          </div>
          <div style={{
            color: "rgba(255,255,255,0.75)", fontSize: 13, lineHeight: 1.6,
            maxHeight: expanded ? "none" : 72, overflow: "hidden",
            transition: "max-height 0.3s",
          }}>
            {content}
          </div>
          <button
            onClick={() => setExpanded(!expanded)}
            style={{
              background: "none", border: "none", color: "#6366f1", cursor: "pointer",
              fontSize: 12, padding: "6px 0 0", fontFamily: "inherit",
            }}
          >
            {expanded ? "Show less ↑" : "Show more ↓"}
          </button>
        </div>
        <GlowButton variant="ghost" onClick={() => onOpenPDF(chunk)} style={{ flexShrink: 0, padding: "6px 12px", fontSize: 12 }}>
          Open Page {chunk.page_number} ↗
        </GlowButton>
      </div>
      {chunk.image_path && (
        <div style={{ marginTop: 12 }}>
          <img src={`${API_BASE}/image?path=${encodeURIComponent(chunk.image_path)}`}
            alt={`Page ${chunk.page_number}`}
            style={{ maxWidth: "100%", borderRadius: 8, border: "1px solid rgba(255,255,255,0.1)" }} />
        </div>
      )}
    </GlassCard>
  );
}

function SourcesRow({ chunks }) {
  const seen = new Set();
  const sources = chunks.filter(({ chunk }) => {
    const key = `${chunk.source_file}:${chunk.page_number}`;
    if (seen.has(key)) return false;
    seen.add(key); return true;
  });
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 20 }}>
      {sources.map(({ chunk }, i) => (
        <div key={i} style={{
          display: "flex", alignItems: "center", gap: 6,
          padding: "6px 12px", borderRadius: 8,
          background: "rgba(255,255,255,0.05)",
          border: "1px solid rgba(255,255,255,0.1)",
          fontSize: 12, color: "rgba(255,255,255,0.7)",
        }}>
          <span style={{ color: "#6366f1" }}>📄</span>
          {chunk.source_file?.split("/").pop()} · p.{chunk.page_number}
        </div>
      ))}
    </div>
  );
}

function Toast({ message, onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 3000); return () => clearTimeout(t); }, []);
  return (
    <div style={{
      position: "fixed", bottom: 24, right: 24, zIndex: 1000,
      background: "rgba(22,22,35,0.95)",
      border: "1px solid rgba(99,102,241,0.4)",
      borderRadius: 12, padding: "14px 20px",
      color: "#a5b4fc", fontSize: 14, fontWeight: 500,
      boxShadow: "0 0 30px rgba(99,102,241,0.2)",
      backdropFilter: "blur(20px)",
      animation: "slideUp 0.3s ease",
    }}>
      {message}
    </div>
  );
}

export default function App() {
  const [file, setFile] = useState(null);
  const [ocrMode, setOcrMode] = useState("Auto Detect");
  const [ingesting, setIngesting] = useState(false);
  const [searchMode, setSearchMode] = useState("All Documents");
  const [docKeyword, setDocKeyword] = useState("");
  const [matchingDocs, setMatchingDocs] = useState([]);
  const [selectedDocs, setSelectedDocs] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState("");
  const [chunks, setChunks] = useState([]);
  const [evaluation, setEvaluation] = useState(null);
  const [evaluationStatus, setEvaluationStatus] = useState("");
  const [pdfChunk, setPdfChunk] = useState(null);
  const [contextOpen, setContextOpen] = useState(false);
  const [toast, setToast] = useState(null);
  const [searchingDocs, setSearchingDocs] = useState(false);

  const showToast = (msg) => setToast(msg);

  const handleIngest = async () => {
    if (!file) return;
    setIngesting(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("ocr_mode", ocrMode);
      await api.ingestDocument(fd);
      showToast("✓ Document ingested successfully");
    } catch {
      showToast("⚠ Backend not connected — UI preview only");
    }
    setIngesting(false);
  };

  const handleDocSearch = useCallback(async (kw) => {
    setDocKeyword(kw);
    if (!kw.trim()) { setMatchingDocs([]); return; }
    setSearchingDocs(true);
    try {
      const data = await api.searchDocuments(kw);
      setMatchingDocs(data.documents || []);
    } catch {
      setMatchingDocs([]);
    }
    setSearchingDocs(false);
  }, []);
  const pollEvaluation = async (evaluationId) => {
    const maxAttempts = 60;

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        const data = await api.getEvaluation(evaluationId);

        setEvaluationStatus(data.status);

        if (data.status === "completed") {
          setEvaluation(data.evaluation);
          return;
        }

        if (data.status === "failed") {
          console.error("Evaluation failed:", data.error);
          return;
        }

        await new Promise((resolve) => setTimeout(resolve, 2000));
      } catch (error) {
        console.error("Could not fetch evaluation:", error);
        return;
      }
    }

    console.warn("Evaluation polling timed out.");
  };
    const handleAsk = async () => {
    if (!query.trim()) {
      showToast("Please enter a question");
      return;
    }

    if (searchMode === "Specific Document" && selectedDocs.length === 0) {
      showToast("Please select at least one document");
      return;
    }

    setLoading(true);
    setAnswer("");
    setChunks([]);
    setEvaluation(null);
    setEvaluationStatus("");

    try {
      const data =
        searchMode === "Specific Document"
          ? await api.retrieveDocument(query, selectedDocs)
          : await api.retrieveAll(query);

      // Display the generated answer immediately
      setAnswer(data.answer || "");

      // Display retrieved chunks
      setChunks(data.chunks || []);

      // Start evaluation polling separately
      if (data.evaluation_id) {
        setEvaluationStatus(data.evaluation_status || "pending");
        pollEvaluation(data.evaluation_id);
      }
    } catch (error) {
      console.error(error);

      setAnswer(
        "⚠ Could not connect to backend. Make sure your Python API server is running on localhost:8000."
      );

      setChunks([]);
    }

    setLoading(false);
  };

  const toggleDoc = (doc) => {
    setSelectedDocs(prev =>
      prev.includes(doc) ? prev.filter(d => d !== doc) : [...prev, doc]
    );
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0a0a0f",
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
      color: "#fff",
      position: "relative",
      overflowX: "hidden",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes ping { 75%, 100% { transform: scale(1.8); opacity: 0; } }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
        @keyframes slideUp { from { transform: translateY(12px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-12px); } }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.3); border-radius: 3px; }
        input::placeholder { color: rgba(255,255,255,0.25); }
      `}</style>

      <GlowOrb style={{ top: -120, left: -120, width: 400, height: 400, background: "rgba(99,102,241,0.35)" }} />
      <GlowOrb style={{ top: 200, right: -100, width: 300, height: 300, background: "rgba(139,92,246,0.25)" }} />
      <GlowOrb style={{ bottom: 100, left: "30%", width: 350, height: 350, background: "rgba(14,165,233,0.15)" }} />
      <GridPattern />

      <div style={{ position: "relative", zIndex: 1, maxWidth: 900, margin: "0 auto", padding: "0 20px 80px" }}>

        {/* Header */}
        <div style={{ textAlign: "center", padding: "60px 0 48px" }}>
          <Badge color="#6366f1">✦ Multimodal RAG</Badge>
          <h1 style={{
            margin: "16px 0 8px",
            fontSize: "clamp(32px, 5vw, 52px)",
            fontWeight: 700,
            background: "linear-gradient(135deg, #fff 30%, #a5b4fc 70%, #8b5cf6 100%)",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
            lineHeight: 1.15,
          }}>
            Ask your documents
          </h1>
          <p style={{ color: "rgba(255,255,255,0.45)", fontSize: 16, margin: 0 }}>
            Ingest PDFs · Retrieve with context · Generate grounded answers
          </p>
        </div>

        {/* Two-column layout */}
        <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 20, alignItems: "start" }}>

          {/* Left sidebar */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

            {/* Upload card */}
            <GlassCard style={{ padding: 20 }}>
              <SectionLabel>Upload Document</SectionLabel>
              <FileDropzone onFile={setFile} file={file} />

              {file && (
                <div style={{ marginTop: 16 }}>
                  <SectionLabel>OCR Mode</SectionLabel>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {["Auto Detect", "Force OCR", "Disable OCR"].map(m => (
                      <label key={m} style={{
                        display: "flex", alignItems: "center", gap: 10, cursor: "pointer",
                        padding: "8px 12px", borderRadius: 8,
                        background: ocrMode === m ? "rgba(99,102,241,0.15)" : "transparent",
                        border: `1px solid ${ocrMode === m ? "rgba(99,102,241,0.4)" : "transparent"}`,
                        transition: "all 0.15s",
                      }}>
                        <div style={{
                          width: 16, height: 16, borderRadius: "50%",
                          border: `2px solid ${ocrMode === m ? "#6366f1" : "rgba(255,255,255,0.2)"}`,
                          display: "flex", alignItems: "center", justifyContent: "center",
                        }}>
                          {ocrMode === m && <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#6366f1" }} />}
                        </div>
                        <input type="radio" checked={ocrMode === m} onChange={() => setOcrMode(m)} style={{ display: "none" }} />
                        <span style={{ fontSize: 13, color: ocrMode === m ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.5)" }}>{m}</span>
                      </label>
                    ))}
                  </div>

                  <GlowButton
                    onClick={handleIngest}
                    disabled={ingesting}
                    style={{ width: "100%", marginTop: 14 }}
                  >
                    {ingesting ? <><Spinner /> Ingesting…</> : "⬆ Ingest Document"}
                  </GlowButton>
                </div>
              )}
            </GlassCard>

            {/* Search mode card */}
            <GlassCard style={{ padding: 20 }}>
              <SectionLabel>Search Scope</SectionLabel>
              <div style={{ display: "flex", gap: 6 }}>
                {["All Documents", "Specific Document"].map(m => (
                  <button
                    key={m}
                    onClick={() => setSearchMode(m)}
                    style={{
                      flex: 1, padding: "8px 4px", borderRadius: 8, cursor: "pointer", border: "none",
                      background: searchMode === m ? "rgba(99,102,241,0.25)" : "rgba(255,255,255,0.05)",
                      color: searchMode === m ? "#a5b4fc" : "rgba(255,255,255,0.4)",
                      fontSize: 12, fontWeight: searchMode === m ? 600 : 400,
                      fontFamily: "inherit",
                      border: searchMode === m ? "1px solid rgba(99,102,241,0.4)" : "1px solid transparent",
                      transition: "all 0.15s",
                    }}
                  >
                    {m === "All Documents" ? "🗂 All" : "📄 Specific"}
                  </button>
                ))}
              </div>

              {searchMode === "Specific Document" && (
                <div style={{ marginTop: 14, animation: "fadeIn 0.3s ease" }}>
                  <AnimatedInput
                    value={docKeyword}
                    onChange={handleDocSearch}
                    placeholder="Filter documents…"
                    icon="🔍"
                  />
                  {searchingDocs && <div style={{ textAlign: "center", padding: 12 }}><Spinner /></div>}
                  {matchingDocs.length > 0 && (
                    <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 4 }}>
                      {matchingDocs.map(doc => (
                        <label key={doc} style={{
                          display: "flex", alignItems: "center", gap: 8, cursor: "pointer",
                          padding: "7px 10px", borderRadius: 8,
                          background: selectedDocs.includes(doc) ? "rgba(99,102,241,0.1)" : "transparent",
                          border: `1px solid ${selectedDocs.includes(doc) ? "rgba(99,102,241,0.3)" : "transparent"}`,
                          transition: "all 0.15s",
                        }}>
                          <div style={{
                            width: 14, height: 14, borderRadius: 3,
                            border: `1.5px solid ${selectedDocs.includes(doc) ? "#6366f1" : "rgba(255,255,255,0.2)"}`,
                            background: selectedDocs.includes(doc) ? "#6366f1" : "transparent",
                            display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9, color: "#fff",
                          }}>
                            {selectedDocs.includes(doc) && "✓"}
                          </div>
                          <input type="checkbox" checked={selectedDocs.includes(doc)} onChange={() => toggleDoc(doc)} style={{ display: "none" }} />
                          <span style={{ fontSize: 12, color: "rgba(255,255,255,0.7)", wordBreak: "break-all" }}>{doc}</span>
                        </label>
                      ))}
                    </div>
                  )}
                  {docKeyword && matchingDocs.length === 0 && !searchingDocs && (
                    <div style={{ color: "rgba(255,255,255,0.3)", fontSize: 12, padding: "10px 0" }}>No matching documents</div>
                  )}
                </div>
              )}
            </GlassCard>
          </div>

          {/* Main content */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

            {/* Query box */}
            <GlassCard glow="#6366f1" style={{ padding: 20 }}>
              <SectionLabel>Ask a Question</SectionLabel>
              <AnimatedInput
                value={query}
                onChange={setQuery}
                placeholder="What does the document say about…"
                icon="✦"
                onEnter={handleAsk}
              />
              <div style={{ marginTop: 12, display: "flex", justifyContent: "flex-end" }}>
                <GlowButton onClick={handleAsk} disabled={loading}>
                  {loading ? <><Spinner /> Retrieving…</> : "Ask ↗"}
                </GlowButton>
              </div>
            </GlassCard>

            {/* Loading state */}
            {loading && (
              <GlassCard style={{ padding: 32, textAlign: "center", animation: "fadeIn 0.3s ease" }}>
                <Spinner />
                <div style={{ color: "rgba(255,255,255,0.5)", fontSize: 14, marginTop: 14 }}>
                  Retrieving relevant chunks and generating answer…
                </div>
                <div style={{ display: "flex", gap: 4, justifyContent: "center", marginTop: 16 }}>
                  {[0, 1, 2].map(i => (
                    <div key={i} style={{
                      width: 6, height: 6, borderRadius: "50%", background: "#6366f1",
                      animation: `ping 1.2s ease ${i * 0.2}s infinite`,
                    }} />
                  ))}
                </div>
              </GlassCard>
            )}

            {/* Answer */}
            {answer && !loading && (
              <div style={{ animation: "fadeIn 0.4s ease" }}>
                <AnswerCard answer={answer} />
              </div>
            )}

            {/* Evaluation */}
            {answer && !loading && evaluationStatus && (
              <div style={{ animation: "fadeIn 0.4s ease" }}>
                <EvaluationCard
                  evaluation={evaluation}
                  status={evaluationStatus}
                />
              </div>
            )}

            {/* Sources */}
            {chunks.length > 0 && !loading && (
              <div style={{ animation: "fadeIn 0.5s ease" }}>
                <SectionLabel>Sources</SectionLabel>
                <SourcesRow chunks={chunks} />

                {/* Retrieved context toggle */}
                <button
                  onClick={() => setContextOpen(!contextOpen)}
                  style={{
                    display: "flex", alignItems: "center", gap: 8,
                    background: "rgba(255,255,255,0.04)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 10, padding: "10px 16px", cursor: "pointer",
                    color: "rgba(255,255,255,0.6)", fontSize: 13, fontFamily: "inherit",
                    width: "100%", marginBottom: contextOpen ? 12 : 0,
                    transition: "all 0.2s",
                  }}
                >
                  <span style={{ marginRight: "auto" }}>Retrieved Context ({chunks.length} chunks)</span>
                  <span style={{
                    transform: contextOpen ? "rotate(180deg)" : "rotate(0deg)",
                    transition: "transform 0.2s", display: "inline-block",
                  }}>▾</span>
                </button>

                {contextOpen && (
                  <div style={{ animation: "fadeIn 0.25s ease" }}>
                    {chunks.map((item, i) => (
                      <ChunkCard
                        key={i}
                        chunk={item.chunk}
                        content={item.retrieved_content}
                        index={i + 1}
                        onOpenPDF={(c) => setPdfChunk(c)}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* PDF viewer panel */}
            {pdfChunk && (
              <div style={{ animation: "fadeIn 0.3s ease" }}>
                <GlassCard glow="#0ea5e9" style={{ padding: 20 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 15 }}>
                        {pdfChunk.source_file?.split("/").pop()}
                      </div>
                      <div style={{ color: "rgba(255,255,255,0.4)", fontSize: 12, marginTop: 2 }}>
                        Page {pdfChunk.page_number}
                      </div>
                    </div>
                    <GlowButton variant="ghost" onClick={() => setPdfChunk(null)} style={{ padding: "6px 12px" }}>
                      ✕ Close
                    </GlowButton>
                  </div>
                  <div style={{
                    borderRadius: 10, overflow: "hidden",
                    border: "1px solid rgba(255,255,255,0.08)",
                    background: "#1a1a2e",
                    display: "flex", justifyContent: "center",
                  }}>
                    <Document
                      file={`${API_BASE}/pdf?path=${encodeURIComponent(pdfChunk.source_file)}`}
                      loading={
                        <div style={{ padding: 40, color: "rgba(255,255,255,0.4)", textAlign: "center" }}>
                          <Spinner /><div style={{ marginTop: 12, fontSize: 13 }}>Loading PDF…</div>
                        </div>
                      }
                      error={
                        <div style={{ padding: 40, color: "#f87171", fontSize: 13, textAlign: "center" }}>
                          Failed to load PDF. Make sure the <code>/pdf</code> endpoint is available.
                        </div>
                      }
                    >
                      <Page
                        pageNumber={pdfChunk.page_number}
                        width={560}
                        renderTextLayer={true}
                        renderAnnotationLayer={false}
                      />
                    </Document>
                  </div>
                </GlassCard>
              </div>
            )}

            {/* Empty state */}
            {!answer && !loading && (
              <GlassCard style={{ padding: 40, textAlign: "center" }}>
                <div style={{ fontSize: 40, marginBottom: 12, animation: "float 4s ease-in-out infinite" }}>✦</div>
                <div style={{ color: "rgba(255,255,255,0.5)", fontSize: 15, fontWeight: 500 }}>
                  Upload a PDF and ask anything
                </div>
                <div style={{ color: "rgba(255,255,255,0.25)", fontSize: 13, marginTop: 6 }}>
                  Supports text, tables, and images via multimodal retrieval
                </div>
              </GlassCard>
            )}
          </div>
        </div>
      </div>

      {toast && <Toast message={toast} onClose={() => setToast(null)} />}
    </div>
  );
}