
import React, { useMemo, useState } from 'react';
import { AnalysisRowResult, TimelineDataPoint, AnalysisCountMode, TimeAggregation, DashboardFilters } from '../types';
import { prepareTimelineData, prepareAuthorTimelineData } from '../services/analysisService';

interface DashboardProps {
  results: AnalysisRowResult[];
  initialCountMode?: AnalysisCountMode;
  onApplyToResults?: (filters: DashboardFilters) => void;
}

type FilterLogic = 'OR' | 'AND';
type DashboardMode = 'LINGUISTIC' | 'AUTHORS';
type AuthorMetric = 'POSTS' | 'WORDS';

const COLORS = [
  '#3b82f6', // blue-500
  '#6366f1', // indigo-500
  '#8b5cf6', // violet-500
  '#d946ef', // fuchsia-500
  '#ec4899', // pink-500
  '#ef4444', // red-500
  '#f59e0b', // amber-500
  '#10b981', // emerald-500
  '#06b6d4', // cyan-500
  '#14b8a6', // teal-500
];

const Dashboard: React.FC<DashboardProps> = ({ results, initialCountMode = AnalysisCountMode.HITS, onApplyToResults }) => {
  const [dashboardMode, setDashboardMode] = useState<DashboardMode>('LINGUISTIC');
  const [selectedTerms, setSelectedTerms] = useState<string[]>([]);
  const [selectedAuthors, setSelectedAuthors] = useState<string[]>([]);
  const [termLogic, setTermLogic] = useState<FilterLogic>('OR');
  const [authorLogic, setAuthorLogic] = useState<FilterLogic>('OR');
  const [keywordFilter, setKeywordFilter] = useState('');
  const [countMode, setCountMode] = useState<AnalysisCountMode>(initialCountMode);
  const [authorMetric, setAuthorMetric] = useState<AuthorMetric>('POSTS');
  const [timeAggregation, setTimeAggregation] = useState<TimeAggregation>(TimeAggregation.DAY);
  const [selectedDateRange, setSelectedDateRange] = useState<{ start: number; end: number } | null>(null);

  const allTerms = useMemo(() => {
    const terms = new Set<string>();
    results.forEach(r => r.matches.forEach(m => terms.add(m.termTitle)));
    return Array.from(terms).sort();
  }, [results]);

  const allAuthors = useMemo(() => {
    const authors = new Set<string>();
    results.forEach(r => r.authors.forEach(a => authors.add(a)));
    return Array.from(authors).sort();
  }, [results]);

  const colorMap = useMemo(() => {
    const map: Record<string, string> = {};
    const list = dashboardMode === 'LINGUISTIC' ? allTerms : allAuthors;
    list.forEach((item, idx) => {
      map[item] = COLORS[idx % COLORS.length];
    });
    return map;
  }, [allTerms, allAuthors, dashboardMode]);

  // --- Linguistic Filtered Results ---
  const filteredResultsLinguistic = useMemo(() => {
    if (dashboardMode !== 'LINGUISTIC') return [];
    return results.filter(res => {
      const matchesKeyword = !keywordFilter || Object.values(res.originalRow).some(v => 
        (typeof v === 'string' ? v : String(v)).toLowerCase().includes(keywordFilter.toLowerCase())
      );
      if (!matchesKeyword) return false;

      if (selectedAuthors.length > 0) {
        if (authorLogic === 'OR') {
          if (!res.authors.some(a => selectedAuthors.includes(a))) return false;
        } else {
          if (!selectedAuthors.every(a => res.authors.includes(a))) return false;
        }
      }

      if (selectedTerms.length > 0) {
        const rowTermTitles = res.matches.map(m => m.termTitle);
        if (termLogic === 'OR') {
          if (!rowTermTitles.some(t => selectedTerms.includes(t))) return false;
        } else {
          if (!selectedTerms.every(t => rowTermTitles.includes(t))) return false;
        }
      }
      return true;
    });
  }, [results, keywordFilter, selectedAuthors, selectedTerms, authorLogic, termLogic, dashboardMode]);

  const timelineLinguistic = useMemo(() => 
    prepareTimelineData(filteredResultsLinguistic, countMode, selectedTerms, timeAggregation), 
    [filteredResultsLinguistic, countMode, selectedTerms, timeAggregation]
  );

  // --- Author Analysis Data ---
  const authorTimeline = useMemo(() => {
    if (dashboardMode !== 'AUTHORS') return [];
    return prepareAuthorTimelineData(results, selectedAuthors, authorMetric, timeAggregation);
  }, [results, selectedAuthors, authorMetric, dashboardMode, timeAggregation]);

  const authorTotals = useMemo(() => {
    const activeAuthors = selectedAuthors.length > 0 ? selectedAuthors : allAuthors;
    let totalPosts = 0;
    let totalWords = 0;

    results.forEach(res => {
      const rowMatchesAuthor = res.authors.some(a => activeAuthors.includes(a));
      if (rowMatchesAuthor) {
        totalPosts++;
        totalWords += res.wordCount;
      }
    });

    return { totalPosts, totalWords };
  }, [results, selectedAuthors, allAuthors]);

  const maxVal = useMemo(() => {
    const data = dashboardMode === 'LINGUISTIC' ? timelineLinguistic : authorTimeline;
    if (data.length === 0) return 0;
    const peak = Math.max(...data.map(d => d.total));
    return peak === 0 ? 1 : peak; // Avoid division by zero
  }, [timelineLinguistic, authorTimeline, dashboardMode]);

  const handleApplyToResults = () => {
    if (onApplyToResults) {
      onApplyToResults({
        selectedTerms: dashboardMode === 'LINGUISTIC' ? selectedTerms : [],
        selectedAuthors,
        keywordFilter: dashboardMode === 'LINGUISTIC' ? keywordFilter : '',
        dateRange: selectedDateRange || undefined
      });
    }
  };

  const toggleDateRange = (range: { start: number; end: number }) => {
    if (selectedDateRange?.start === range.start && selectedDateRange?.end === range.end) {
      setSelectedDateRange(null);
    } else {
      setSelectedDateRange(range);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-700 pb-12">
      {/* Dashboard Mode Switcher */}
      <div className="flex flex-col md:flex-row justify-center items-center gap-6">
        <div className="bg-slate-200/50 p-1 rounded-2xl flex gap-1 shadow-inner border border-slate-100">
          <button 
            onClick={() => { setDashboardMode('LINGUISTIC'); setSelectedDateRange(null); }}
            className={`px-6 py-2.5 rounded-xl text-sm font-bold transition-all flex items-center gap-2 ${dashboardMode === 'LINGUISTIC' ? 'bg-white text-blue-600 shadow-md' : 'text-slate-500 hover:text-slate-700'}`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" /></svg>
            Linguistic View
          </button>
          <button 
            onClick={() => { setDashboardMode('AUTHORS'); setSelectedDateRange(null); }}
            className={`px-6 py-2.5 rounded-xl text-sm font-bold transition-all flex items-center gap-2 ${dashboardMode === 'AUTHORS' ? 'bg-white text-indigo-600 shadow-md' : 'text-slate-500 hover:text-slate-700'}`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
            Author View
          </button>
        </div>

        <button 
          onClick={handleApplyToResults}
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-bold shadow-lg flex items-center gap-2 transition-all active:scale-95"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg>
          Sync Filters to Results Table
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Filters Sidebar */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 h-fit">
            <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-6">Visual Filters</h4>
            
            <div className="space-y-6">
              {dashboardMode === 'LINGUISTIC' && (
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-2">Keyword Filter</label>
                  <input 
                    type="text"
                    placeholder="Type to filter rows..."
                    className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                    value={keywordFilter}
                    onChange={(e) => setKeywordFilter(e.target.value)}
                  />
                </div>
              )}

              {allAuthors.length > 0 && (
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <div className="flex items-center gap-2">
                      <label className="text-xs font-bold text-slate-700">Authors</label>
                      {dashboardMode === 'LINGUISTIC' && (
                        <div className="flex bg-slate-100 p-0.5 rounded-md">
                          <button onClick={() => setAuthorLogic('OR')} className={`px-1.5 py-0.5 text-[8px] font-bold rounded ${authorLogic === 'OR' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-400'}`}>Either</button>
                          <button onClick={() => setAuthorLogic('AND')} className={`px-1.5 py-0.5 text-[8px] font-bold rounded ${authorLogic === 'AND' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-400'}`}>Both</button>
                        </div>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => setSelectedAuthors([...allAuthors])} className="text-[10px] text-blue-600 font-bold hover:underline">All</button>
                      <button onClick={() => setSelectedAuthors([])} className="text-[10px] text-slate-400 font-bold hover:underline">None</button>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1.5 max-h-[150px] overflow-y-auto p-1 border border-slate-50 rounded-lg bg-slate-50/30">
                    {allAuthors.map(author => (
                      <button
                        key={author}
                        onClick={() => setSelectedAuthors(prev => prev.includes(author) ? prev.filter(a => a !== author) : [...prev, author])}
                        className={`px-2 py-1 rounded-md text-[10px] font-bold border transition-all ${
                          selectedAuthors.includes(author)
                            ? 'bg-indigo-600 border-indigo-600 text-white'
                            : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50'
                        }`}
                      >
                        {author}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {dashboardMode === 'LINGUISTIC' && (
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <div className="flex items-center gap-2">
                      <label className="text-xs font-bold text-slate-700">Linguistic Terms</label>
                      <div className="flex bg-slate-100 p-0.5 rounded-md">
                        <button onClick={() => setTermLogic('OR')} className={`px-1.5 py-0.5 text-[8px] font-bold rounded ${termLogic === 'OR' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400'}`}>Either</button>
                        <button onClick={() => setTermLogic('AND')} className={`px-1.5 py-0.5 text-[8px] font-bold rounded ${termLogic === 'AND' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400'}`}>Both</button>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => setSelectedTerms([...allTerms])} className="text-[10px] text-blue-600 font-bold hover:underline">All</button>
                      <button onClick={() => setSelectedTerms([])} className="text-[10px] text-slate-400 font-bold hover:underline">None</button>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2 max-h-[250px] overflow-y-auto p-1">
                    {allTerms.map(term => (
                      <button
                        key={term}
                        onClick={() => setSelectedTerms(prev => prev.includes(term) ? prev.filter(t => t !== term) : [...prev, term])}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all flex items-center gap-2 ${
                          selectedTerms.includes(term)
                            ? 'border-slate-800 bg-slate-800 text-white shadow-md'
                            : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                        }`}
                      >
                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: colorMap[term] }}></div>
                        {term}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 space-y-4">
             <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Grand Totals</h4>
             {dashboardMode === 'LINGUISTIC' ? (
                <div>
                   <div className="text-2xl font-bold text-blue-600">{filteredResultsLinguistic.length.toLocaleString()}</div>
                   <p className="text-xs text-slate-500 font-medium">Matching Posts Across Period</p>
                </div>
             ) : (
                <div className="space-y-4">
                   <div>
                      <div className="text-2xl font-bold text-indigo-600">{authorTotals.totalPosts.toLocaleString()}</div>
                      <p className="text-xs text-slate-500 font-medium">Posts by Selection (Period)</p>
                   </div>
                   <div>
                      <div className="text-2xl font-bold text-emerald-600">{authorTotals.totalWords.toLocaleString()}</div>
                      <p className="text-xs text-slate-500 font-medium">Words by Selection (Period)</p>
                   </div>
                </div>
             )}
          </div>
        </div>

        {/* Main Content Area */}
        <div className="lg:col-span-3 space-y-6 overflow-hidden">
          <div className="bg-white p-6 md:p-8 rounded-2xl shadow-sm border border-slate-100 w-full flex flex-col">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
              <div>
                <h3 className="text-xl font-bold text-slate-800">
                   {dashboardMode === 'LINGUISTIC' ? 'Extraction Timeline' : 'Author Productivity Timeline'}
                </h3>
                <p className="text-sm text-slate-500">
                  {dashboardMode === 'LINGUISTIC' 
                    ? (countMode === AnalysisCountMode.ROWS ? 'Presence of terms per unique row' : 'Sum of occurrences for selected terms')
                    : (authorMetric === 'POSTS' ? 'Number of posts contributed' : 'Volume of words contributed')
                  }
                  {selectedDateRange && <span className="ml-2 px-2 py-0.5 bg-amber-100 text-amber-800 font-bold rounded text-[10px]">Slice Filter Active</span>}
                </p>
              </div>

              <div className="flex flex-col items-end gap-2">
                <div className="flex bg-slate-100 p-1 rounded-xl shrink-0">
                  <button 
                    onClick={() => setTimeAggregation(TimeAggregation.DAY)}
                    className={`px-3 py-1 text-[10px] font-bold rounded-lg transition-all ${timeAggregation === TimeAggregation.DAY ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-400'}`}
                  >Daily</button>
                  <button 
                    onClick={() => setTimeAggregation(TimeAggregation.MONTH)}
                    className={`px-3 py-1 text-[10px] font-bold rounded-lg transition-all ${timeAggregation === TimeAggregation.MONTH ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-400'}`}
                  >Monthly</button>
                  <button 
                    onClick={() => setTimeAggregation(TimeAggregation.YEAR)}
                    className={`px-3 py-1 text-[10px] font-bold rounded-lg transition-all ${timeAggregation === TimeAggregation.YEAR ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-400'}`}
                  >Yearly</button>
                </div>

                <div className="flex bg-slate-100 p-1 rounded-xl shrink-0">
                  {dashboardMode === 'LINGUISTIC' ? (
                    <>
                      <button onClick={() => setCountMode(AnalysisCountMode.HITS)} className={`px-4 py-1.5 text-[11px] font-bold rounded-lg transition-all ${countMode === AnalysisCountMode.HITS ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}>Hits</button>
                      <button onClick={() => setCountMode(AnalysisCountMode.ROWS)} className={`px-4 py-1.5 text-[11px] font-bold rounded-lg transition-all ${countMode === AnalysisCountMode.ROWS ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}>Rows</button>
                    </>
                  ) : (
                    <>
                      <button onClick={() => setAuthorMetric('POSTS')} className={`px-4 py-1.5 text-[11px] font-bold rounded-lg transition-all ${authorMetric === 'POSTS' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}>Posts</button>
                      <button onClick={() => setAuthorMetric('WORDS')} className={`px-4 py-1.5 text-[11px] font-bold rounded-lg transition-all ${authorMetric === 'WORDS' ? 'bg-white text-emerald-600 shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}>Words</button>
                    </>
                  )}
                </div>
              </div>
            </div>

            <div className="w-full overflow-x-auto pb-12 custom-scrollbar">
              <div className="relative h-[400px] flex items-end gap-1 px-4 border-b border-l border-slate-100 min-w-full">
                {(dashboardMode === 'LINGUISTIC' ? timelineLinguistic : authorTimeline).length === 0 ? (
                  <div className="absolute inset-0 flex items-center justify-center text-slate-300 italic text-sm">No data for selected filters</div>
                ) : (
                  (dashboardMode === 'LINGUISTIC' ? timelineLinguistic : authorTimeline).map((point, idx) => {
                    const isSliceSelected = selectedDateRange?.start === point.dateRange.start && selectedDateRange?.end === point.dateRange.end;
                    
                    return (
                      <div 
                        key={point.timestamp} 
                        onClick={() => toggleDateRange(point.dateRange)}
                        className={`flex-1 min-w-[40px] group relative flex flex-col items-center justify-end h-full transition-all cursor-pointer ${isSliceSelected ? 'bg-amber-50/50' : 'hover:bg-slate-50'}`}
                      >
                        {/* Bar Content Wrapper */}
                        <div className="w-full h-full flex flex-col-reverse justify-start">
                          {(Object.entries(point.counts) as [string, number][])
                            .filter(([item]) => {
                               const list = dashboardMode === 'LINGUISTIC' ? selectedTerms : selectedAuthors;
                               return list.length === 0 || list.includes(item);
                            })
                            .map(([item, count]) => {
                              const segmentHeight = (count / maxVal) * 100;
                              return (
                                <div 
                                  key={item}
                                  style={{ height: `${segmentHeight}%`, backgroundColor: colorMap[item] }}
                                  className="w-full rounded-sm opacity-80 hover:opacity-100 transition-all group/segment relative"
                                >
                                   {/* Segment Specific Tooltip */}
                                   <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover/segment:block z-30 pointer-events-none">
                                      <div className="bg-slate-800 text-white px-2 py-1 rounded text-[10px] whitespace-nowrap shadow-lg border border-slate-700">
                                        <span className="font-bold">{item}:</span> {count.toLocaleString()}
                                      </div>
                                   </div>
                                </div>
                              );
                            })}
                        </div>
                        
                        {/* Summary Tooltip (Visible when hovering the entire bar) */}
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-6 hidden group-hover:block z-20 w-48 pointer-events-none">
                          <div className="bg-slate-900 text-white p-3 rounded-xl shadow-2xl text-xs border border-white/10">
                            <div className="font-bold border-b border-white/20 pb-1 mb-2 flex justify-between">
                              <span>{point.label}</span>
                              {isSliceSelected && <span className="text-amber-400">Selected</span>}
                            </div>
                            <div className="space-y-1">
                              <div className="flex justify-between mb-1">
                                <span>Total:</span>
                                <span className="font-bold">{point.total.toLocaleString()}</span>
                              </div>
                              {(Object.entries(point.counts) as [string, number][]).sort((a, b) => b[1] - a[1]).slice(0, 10).map(([item, count]) => (
                                <div key={item} className="flex justify-between items-center text-[10px]">
                                  <div className="flex items-center gap-1.5 overflow-hidden">
                                    <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: colorMap[item] }}></div>
                                    <span className="truncate">{item}:</span>
                                  </div>
                                  <span className="ml-2 font-mono">{count.toLocaleString()}</span>
                                </div>
                              ))}
                            </div>
                            <div className="mt-2 pt-1 border-t border-white/10 text-[9px] text-slate-400 italic text-center">Click to filter results to this slice</div>
                          </div>
                        </div>

                        {/* X-Axis Labels */}
                        {(idx % Math.ceil((dashboardMode === 'LINGUISTIC' ? timelineLinguistic : authorTimeline).length / 8) === 0) && (
                          <div className={`absolute top-full mt-2 text-[9px] font-bold rotate-45 origin-top-left whitespace-nowrap ${isSliceSelected ? 'text-blue-600 scale-110' : 'text-slate-400'}`}>
                            {point.label}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            <div className="mt-8 pt-6 border-t border-slate-50">
              <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">Legend (First 50 Items)</h4>
              <div className="flex flex-wrap gap-x-6 gap-y-3">
                {(dashboardMode === 'LINGUISTIC' ? (selectedTerms.length > 0 ? selectedTerms : allTerms) : (selectedAuthors.length > 0 ? selectedAuthors : allAuthors)).slice(0, 50).map(item => (
                  <div key={item} className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: colorMap[item] }}></div>
                    <span className="text-xs font-semibold text-slate-700">{item}</span>
                  </div>
                ))}
                {(dashboardMode === 'LINGUISTIC' ? allTerms : allAuthors).length > 50 && <span className="text-[10px] text-slate-400 font-bold">...and {(dashboardMode === 'LINGUISTIC' ? allTerms : allAuthors).length - 50} more</span>}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
             <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-between">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">Top Volume Items</h4>
                <div className="space-y-3">
                  {(() => {
                    const data = dashboardMode === 'LINGUISTIC' ? timelineLinguistic : authorTimeline;
                    const totals: Record<string, number> = {};
                    data.forEach(p => (Object.entries(p.counts) as [string, number][]).forEach(([t, c]) => totals[t] = (totals[t] || 0) + c));
                    const sorted = (Object.entries(totals) as [string, number][]).sort((a,b) => b[1] - a[1]).slice(0, 5);
                    
                    if (sorted.length === 0) return <div className="text-slate-300 italic text-sm">No activity recorded</div>;

                    return sorted.map(([item, count]) => (
                      <div key={item} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: colorMap[item] }}></div>
                          <span className="text-xs font-bold text-slate-700">{item}</span>
                        </div>
                        <span className="text-xs font-mono font-bold text-slate-400">{count.toLocaleString()}</span>
                      </div>
                    ));
                  })()}
                </div>
             </div>
             
             <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">Total Coverage Period</h4>
                {results.length > 0 ? (
                  <div className="space-y-4">
                     <div>
                        <div className="text-lg font-bold text-slate-800">
                           {results.reduce((min, r) => r.date && r.date < min ? r.date : min, results[0].date || new Date()).toLocaleDateString()}
                        </div>
                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-tight">First Analyzed Record</p>
                     </div>
                     <div>
                        <div className="text-lg font-bold text-slate-800">
                           {results.reduce((max, r) => r.date && r.date > max ? r.date : max, results[0].date || new Date()).toLocaleDateString()}
                        </div>
                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-tight">Last Analyzed Record</p>
                     </div>
                  </div>
                ) : <div className="text-slate-300 italic text-sm">No date data available</div>}
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
