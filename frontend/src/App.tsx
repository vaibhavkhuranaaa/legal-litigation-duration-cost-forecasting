import { useEffect, useRef, useState } from "react";

import {
  api,
  type Benchmark,
  type PopulationExplorer,
  type Portfolio,
  type Provenance,
} from "./api";
import { ReportWorkspace } from "./ReportWorkspace";
import { parseReportState, reportUrl, type ReportState } from "./report-state";

type DataBundle = {
  portfolio: Portfolio;
  explorer: PopulationExplorer;
  benchmark: Benchmark;
  provenance: Provenance;
};

type LoadState =
  | { status: "loading" }
  | { status: "ready"; data: DataBundle }
  | { status: "cancelled" }
  | { status: "error"; message: string };

function validState(state: ReportState, explorer: PopulationExplorer): ReportState {
  const districtValid = state.districtCode === "all" || explorer.dimensions.districts.some((item) => item.district_code === state.districtCode);
  const natureValid = state.natureFamily === "all" || explorer.dimensions.nature_families.includes(state.natureFamily);
  return {
    ...state,
    districtCode: districtValid ? state.districtCode : "all",
    natureFamily: natureValid ? state.natureFamily : "all",
  };
}

function App() {
  const [reportState, setReportState] = useState(() => parseReportState(window.location.search));
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });
  const [requestKey, setRequestKey] = useState(0);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => {
    const nextController = new AbortController();
    controller.current = nextController;
    let mounted = true;
    setLoadState({ status: "loading" });
    Promise.all([
      api.portfolio(nextController.signal),
      api.explorer(nextController.signal),
      api.benchmark(reportState.cohort, nextController.signal),
      api.provenance(nextController.signal),
    ]).then(([portfolio, explorer, benchmark, provenance]) => {
      if (!mounted) return;
      const normalized = validState(reportState, explorer);
      setReportState(normalized);
      window.history.replaceState(null, "", reportUrl(normalized, window.location.pathname));
      setLoadState({ status: "ready", data: { portfolio, explorer, benchmark, provenance } });
    }).catch((reason: unknown) => {
      if (!mounted) return;
      if (reason instanceof DOMException && reason.name === "AbortError") setLoadState({ status: "cancelled" });
      else setLoadState({ status: "error", message: reason instanceof Error ? reason.message : "Data request failed" });
    });
    return () => {
      mounted = false;
      nextController.abort();
    };
  }, [requestKey]);

  useEffect(() => {
    function restoreFromHistory() {
      const next = parseReportState(window.location.search);
      setReportState(loadState.status === "ready" ? validState(next, loadState.data.explorer) : next);
    }
    window.addEventListener("popstate", restoreFromHistory);
    return () => window.removeEventListener("popstate", restoreFromHistory);
  }, [loadState]);

  function updateState(next: ReportState, mode: "push" | "replace") {
    const normalized = loadState.status === "ready" ? validState(next, loadState.data.explorer) : next;
    setReportState(normalized);
    window.history[`${mode}State`](null, "", reportUrl(normalized, window.location.pathname));
    if (loadState.status === "ready" && normalized.cohort !== reportState.cohort) {
      api.benchmark(normalized.cohort).then((benchmark) => {
        setLoadState((current) => current.status === "ready" ? { ...current, data: { ...current.data, benchmark } } : current);
      }).catch((reason: unknown) => {
        setLoadState({ status: "error", message: reason instanceof Error ? reason.message : "Benchmark request failed" });
      });
    }
  }

  if (loadState.status === "loading") {
    return <main className="loading-state" aria-busy="true"><span className="loading-line" /><span className="loading-line wide" /><span className="loading-block" /><p>Loading governed report workspace</p><button className="button-secondary" type="button" onClick={() => controller.current?.abort()}>Cancel data load</button></main>;
  }

  if (loadState.status === "cancelled") {
    return <main className="fatal-state cancelled-state" role="status"><h1>Load cancelled: the report request was stopped</h1><p>Your URL state is preserved. Retry when you are ready to restore the same analytical context.</p><button className="button-primary" type="button" onClick={() => setRequestKey((value) => value + 1)}>Retry data load</button></main>;
  }

  if (loadState.status === "error") {
    return <main className="fatal-state" role="alert"><h1>Connection error: portfolio evidence did not load</h1><p>{loadState.message}. Start the local API or refresh the static artifact, then retry.</p><button className="button-primary" type="button" onClick={() => setRequestKey((value) => value + 1)}>Retry data load</button></main>;
  }

  return <ReportWorkspace {...loadState.data} state={reportState} onStateChange={updateState} />;
}

export default App;
