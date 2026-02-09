
import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { CorpusRow, SearchMode, AnalysisRowResult, SearchExpression, AnalysisOptions, CorpusStats, AnalysisCountMode, DashboardFilters } from './types';
import { SEARCH_EXPRESSIONS, Icons } from './constants';
import { parseTSV, analyzeCorpus, calculateCorpusStats } from './services/analysisService';
import FileUpload from './components/FileUpload';
import Configuration from './components/Configuration';
import ResultsTable from './components/ResultsTable';
import TermEditorModal from './components/TermEditorModal';
import Dashboard from './components/Dashboard';

enum AppStep {
  UPLOAD = 'UPLOAD',
  CONFIGURE = 'CONFIGURE',
  RESULTS = 'RESULTS',
  DASHBOARD = 'DASHBOARD'
}

const STORAGE_KEY = 'linguist_search_expressions';

const App: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<AppStep>(AppStep.UPLOAD);
  const [corpusData, setCorpusData] = useState<CorpusRow[]>([]);
  const [headers, setHeaders] = useState<string[]>([]);
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  
  // Expressions state with persistence
  const [expressions, setExpressions] = useState<SearchExpression[]>([]);
  
  const [analysisOptions, setAnalysisOptions] = useState<AnalysisOptions>({
    includeEnglish: true,
    includeHebrew: true,
    mode: SearchMode.CONCATENATED,
    countMode: AnalysisCountMode.HITS,
    dateColumn: undefined
  });

  const [analysisResults, setAnalysisResults] = useState<AnalysisRowResult[]>([]);
  const [corpusStats, setCorpusStats] = useState<CorpusStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  // Global filters synchronized from Dashboard
  const [appliedFilters, setAppliedFilters] = useState<DashboardFilters | null>(null);

  // Editor state
  const [editingTerm, setEditingTerm] = useState<SearchExpression | null>(null);
  const [isEditorOpen, setIsEditorOpen] = useState(false);

  // Initialize expressions from local storage or constants
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        setExpressions(JSON.parse(saved));
      } catch (e) {
        setExpressions(SEARCH_EXPRESSIONS);
      }
    } else {
      setExpressions(SEARCH_EXPRESSIONS);
    }
  }, []);

  // Persist expressions on change
  useEffect(() => {
    if (expressions.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(expressions));
    }
  }, [expressions]);

  const handleDataLoaded = useCallback((data: any[]) => {
    const rawText = data[0]._raw;
    const parsed = parseTSV(rawText);
    if (parsed.length > 0) {
      setCorpusData(parsed);
      setHeaders(Object.keys(parsed[0]));
      // Automatically try to detect a date column with more keywords
      const possibleDateCols = ["date", "year", "time", "timestamp", "period", "תאריך", "שנה", "created", "posted", "day", "month"];
      const detected = Object.keys(parsed[0]).find(h => possibleDateCols.some(pc => h.toLowerCase().includes(pc)));
      if (detected) {
        setAnalysisOptions(prev => ({ ...prev, dateColumn: detected }));
      }
      setCurrentStep(AppStep.CONFIGURE);
    }
  }, []);

  const toggleColumn = useCallback((header: string) => {
    setSelectedColumns(prev => 
      prev.includes(header) 
        ? prev.filter(h => h !== header) 
        : [...prev, header]
    );
  }, []);

  const toggleExpression = useCallback((id: string) => {
    setExpressions(prev => prev.map(exp => 
      exp.id === id ? { ...exp, enabled: exp.enabled === false ? true : false } : exp
    ));
  }, []);

  const bulkExpressions = useCallback((type: 'ALL' | 'NONE' | 'ENGLISH' | 'HEBREW') => {
    setExpressions(prev => prev.map(exp => {
      let enabled = true;
      if (type === 'NONE') enabled = false;
      if (type === 'ENGLISH' && !exp.regex_en) enabled = false;
      if (type === 'HEBREW' && !exp.regex_he) enabled = false;
      return { ...exp, enabled };
    }));
  }, []);

  const runAnalysis = async () => {
    setIsLoading(true);
    setAppliedFilters(null); // Clear previous filters
    setTimeout(async () => {
      const results = await analyzeCorpus(
        corpusData,
        selectedColumns,
        expressions,
        analysisOptions
      );
      
      const stats = calculateCorpusStats(corpusData, selectedColumns);
      
      setAnalysisResults(results);
      setCorpusStats(stats);
      setIsLoading(false);
      setCurrentStep(AppStep.RESULTS);
    }, 100);
  };

  const handleApplyDashboardFilters = (filters: DashboardFilters) => {
    setAppliedFilters(filters);
    setCurrentStep(AppStep.RESULTS);
  };

  const saveExpression = (term: SearchExpression) => {
    setExpressions(prev => {
      const exists = prev.find(e => e.id === term.id);
      if (exists) {
        return prev.map(e => e.id === term.id ? term : e);
      }
      return [...prev, term];
    });
    setIsEditorOpen(false);
    setEditingTerm(null);
  };

  const deleteExpression = (id: string) => {
    setExpressions(prev => prev.filter(e => e.id !== id));
    setIsEditorOpen(false);
    setEditingTerm(null);
  };

  const reset = () => {
    setCorpusData([]);
    setHeaders([]);
    setSelectedColumns([]);
    setAnalysisResults([]);
    setCorpusStats(null);
    setAppliedFilters(null);
    setCurrentStep(AppStep.UPLOAD);
  };

  const breadcrumbs = useMemo(() => [
    { step: AppStep.UPLOAD, label: 'Upload', icon: <Icons.Upload /> },
    { step: AppStep.CONFIGURE, label: 'Configure', icon: <Icons.Chart /> },
    { step: AppStep.RESULTS, label: 'Results', icon: <Icons.FileText /> },
    { step: AppStep.DASHBOARD, label: 'Dashboard', icon: <Icons.Chart /> },
  ], []);

  return (
    <div className="min-h-screen pb-20">
      <header className="bg-white border-b border-slate-200 px-6 py-4 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="bg-blue-600 p-2 rounded-lg text-white">
              <Icons.Chart />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">Linguist</h1>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-widest">Corpus Analysis Tool</p>
            </div>
          </div>

          <nav className="flex items-center bg-slate-100 p-1 rounded-xl">
            {breadcrumbs.map((crumb, idx) => (
              <React.Fragment key={crumb.step}>
                <button 
                  onClick={() => {
                    if (crumb.step === AppStep.UPLOAD) reset();
                    else if (crumb.step === AppStep.RESULTS && analysisResults.length > 0) setCurrentStep(AppStep.RESULTS);
                    else if (crumb.step === AppStep.CONFIGURE && corpusData.length > 0) setCurrentStep(AppStep.CONFIGURE);
                    else if (crumb.step === AppStep.DASHBOARD && analysisResults.length > 0) setCurrentStep(AppStep.DASHBOARD);
                  }}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                    currentStep === crumb.step 
                      ? 'bg-white text-blue-600 shadow-sm' 
                      : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  <span className="opacity-70 scale-75">{crumb.icon}</span>
                  {crumb.label}
                </button>
                {idx < breadcrumbs.length - 1 && (
                  <div className="w-4 flex justify-center text-slate-300">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                  </div>
                )}
              </React.Fragment>
            ))}
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-12">
        {isLoading && (
          <div className="fixed inset-0 bg-slate-900/10 backdrop-blur-[2px] z-[100] flex items-center justify-center">
            <div className="bg-white p-8 rounded-2xl shadow-xl flex flex-col items-center">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent mb-4"></div>
              <p className="font-bold text-slate-800">Processing Corpus...</p>
              <p className="text-sm text-slate-500 mt-1">Applying linguistic regex patterns</p>
            </div>
          </div>
        )}

        {currentStep === AppStep.UPLOAD && (
          <FileUpload onDataLoaded={handleDataLoaded} isLoading={isLoading} />
        )}

        {currentStep === AppStep.CONFIGURE && (
          <Configuration 
            headers={headers}
            selectedColumns={selectedColumns}
            expressions={expressions}
            analysisOptions={analysisOptions}
            onToggleColumn={toggleColumn}
            onToggleExpression={toggleExpression}
            onSetAnalysisOptions={setAnalysisOptions}
            onRunAnalysis={runAnalysis}
            onAddNewExpression={() => { setEditingTerm(null); setIsEditorOpen(true); }}
            onEditExpression={(term) => { setEditingTerm(term); setIsEditorOpen(true); }}
            onBulkExpressions={bulkExpressions}
          />
        )}

        {currentStep === AppStep.RESULTS && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              {appliedFilters && (
                <div className="bg-amber-50 border border-amber-200 px-4 py-2 rounded-xl flex items-center gap-3">
                  <span className="text-xs font-bold text-amber-700">Dashboard filters applied</span>
                  <button 
                    onClick={() => setAppliedFilters(null)}
                    className="text-[10px] bg-white border border-amber-300 px-2 py-1 rounded hover:bg-amber-100 font-bold text-amber-800"
                  >
                    Clear Filters
                  </button>
                </div>
              )}
              <div className="flex-1 flex justify-end">
                <button 
                  onClick={() => setCurrentStep(AppStep.DASHBOARD)}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-bold shadow-lg flex items-center gap-2 transition-all active:scale-95"
                >
                  <Icons.Chart />
                  View Dashboard
                </button>
              </div>
            </div>
            <ResultsTable 
              results={analysisResults} 
              stats={corpusStats} 
              selectedColumns={selectedColumns}
              countMode={analysisOptions.countMode}
              externalFilters={appliedFilters}
              onReset={reset} 
            />
          </div>
        )}

        {currentStep === AppStep.DASHBOARD && (
          <div className="space-y-6">
            <div className="flex justify-start">
               <button 
                onClick={() => setCurrentStep(AppStep.RESULTS)}
                className="text-slate-600 hover:text-blue-600 px-4 py-2 rounded-xl font-bold flex items-center gap-2 transition-all"
              >
                <Icons.FileText />
                Back to Results
              </button>
            </div>
            <Dashboard 
              results={analysisResults} 
              initialCountMode={analysisOptions.countMode} 
              onApplyToResults={handleApplyDashboardFilters}
            />
          </div>
        )}
      </main>

      {isEditorOpen && (
        <TermEditorModal 
          term={editingTerm}
          onSave={saveExpression}
          onClose={() => setIsEditorOpen(false)}
          onDelete={deleteExpression}
        />
      )}

      <footer className="fixed bottom-0 left-0 right-0 py-4 px-8 flex justify-center pointer-events-none z-40">
        <div className="bg-white/80 backdrop-blur border border-slate-200 px-6 py-2 rounded-full shadow-lg pointer-events-auto">
          <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest flex items-center gap-4">
            <span>Powered by Gemini & Regex Analysis</span>
            <span className="w-1 h-1 bg-slate-200 rounded-full"></span>
            <span>{expressions.length} Search Expressions Loaded</span>
          </p>
        </div>
      </footer>
    </div>
  );
};

export default App;
