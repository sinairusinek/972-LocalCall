
import React, { useState, useMemo } from 'react';
import { AnalysisRowResult, CorpusStats, AnalysisCountMode, DashboardFilters } from '../types';
import { Icons as AppIcons } from '../constants';
import { generateResultsTSV } from '../services/analysisService';

interface ResultsTableProps {
  results: AnalysisRowResult[];
  stats: CorpusStats | null;
  selectedColumns: string[];
  countMode: AnalysisCountMode;
  externalFilters?: DashboardFilters | null;
  onReset: () => void;
}

const ResultsTable: React.FC<ResultsTableProps> = ({ results, stats, selectedColumns, countMode, externalFilters, onReset }) => {
  const [searchTerm, setSearchTerm] = useState('');
  
  const headers = results.length > 0 ? Object.keys(results[0].originalRow) : [];
  
  const finalResults = useMemo(() => {
    let filtered = results;

    // Apply internal search term
    if (searchTerm) {
      filtered = filtered.filter(res => {
        const combined = Object.values(res.originalRow).join(' ').toLowerCase();
        const matches = res.matches.map(m => m.termTitle.toLowerCase()).join(' ');
        return combined.includes(searchTerm.toLowerCase()) || matches.includes(searchTerm.toLowerCase());
      });
    }

    // Apply dashboard synchronization filters
    if (externalFilters) {
      const { selectedTerms, selectedAuthors, keywordFilter, dateRange } = externalFilters;

      if (keywordFilter) {
        filtered = filtered.filter(res => 
          Object.values(res.originalRow).some(v => String(v).toLowerCase().includes(keywordFilter.toLowerCase()))
        );
      }

      if (selectedTerms && selectedTerms.length > 0) {
        filtered = filtered.filter(res => 
          res.matches.some(m => selectedTerms.includes(m.termTitle))
        );
      }

      if (selectedAuthors && selectedAuthors.length > 0) {
        filtered = filtered.filter(res => 
          res.authors.some(a => selectedAuthors.includes(a))
        );
      }

      if (dateRange && dateRange.start && dateRange.end) {
        filtered = filtered.filter(res => {
          if (!res.date) return false;
          const ts = res.date.getTime();
          return ts >= dateRange.start && ts <= dateRange.end;
        });
      }
    }

    return filtered;
  }, [results, searchTerm, externalFilters]);

  const handleDownload = () => {
    const tsv = generateResultsTSV(finalResults);
    const blob = new Blob([tsv], { type: 'text/tab-separated-values' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analysis_results_${new Date().toISOString().slice(0, 10)}.tsv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const isRowMode = countMode === AnalysisCountMode.ROWS;

  return (
    <div className="space-y-6 animate-in fade-in duration-700">
      {/* Stats Summary Section */}
      {stats && (
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <div className="flex flex-wrap gap-8 items-center justify-between mb-6">
            <div className="flex gap-8">
              <div className="flex flex-col">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Grand Total Rows</span>
                <span className="text-2xl font-bold text-slate-800">{stats.totalRows.toLocaleString()}</span>
              </div>
              <div className="flex flex-col border-l border-slate-100 pl-8">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Grand Total Words</span>
                <span className="text-2xl font-bold text-slate-800">{stats.totalWords.toLocaleString()}</span>
              </div>
            </div>
            <div className="text-[11px] font-medium text-slate-400 italic">
              * Statistics calculated across {selectedColumns.length} selected search columns.
            </div>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {selectedColumns.map(col => {
              const colStat = stats.columnStats[col];
              return (
                <div key={col} className="bg-slate-50 p-3 rounded-xl border border-slate-100 flex flex-col">
                  <span className="text-[10px] font-bold text-slate-500 uppercase truncate mb-1" title={col}>{col}</span>
                  <div className="flex justify-between items-end">
                    <div className="flex flex-col">
                      <span className="text-[10px] text-slate-400">Non-empty rows</span>
                      <span className="text-sm font-bold text-slate-700">{colStat?.nonEmptyRows.toLocaleString() || 0}</span>
                    </div>
                    <div className="flex flex-col items-end">
                      <span className="text-[10px] text-slate-400 text-right">Words</span>
                      <span className="text-sm font-bold text-blue-600">{colStat?.wordCount.toLocaleString() || 0}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Actions & Search */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
        <div>
          <h3 className="text-xl font-bold text-slate-800">Extraction Results</h3>
          <p className="text-sm text-slate-500">
            {finalResults.length} rows shown • 
            <span className="font-bold ml-1 text-indigo-600 uppercase text-[10px]">
              {isRowMode ? 'Presence Mode' : 'Frequency Mode'}
            </span>
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <AppIcons.Search />
            </div>
            <input 
              type="text" 
              placeholder="Search results..."
              className="pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <button 
            onClick={handleDownload}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <AppIcons.Download />
            Download TSV
          </button>
          <button 
            onClick={onReset}
            className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg text-sm font-medium transition-colors border border-slate-200"
          >
            New Analysis
          </button>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="overflow-x-auto max-h-[70vh]">
          <table className="w-full text-left border-collapse min-w-[800px]">
            <thead className="sticky top-0 bg-slate-50 z-10">
              <tr>
                {headers.slice(0, 4).map(h => (
                  <th key={h} className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-slate-100">{h}</th>
                ))}
                <th className="px-6 py-4 text-xs font-bold text-blue-600 uppercase tracking-wider border-b border-slate-100">Found Terms</th>
                <th className="px-6 py-4 text-xs font-bold text-blue-600 uppercase tracking-wider border-b border-slate-100 text-center">
                  {isRowMode ? 'Found' : 'Hits'}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {finalResults.map((res, i) => (
                <tr key={i} className="hover:bg-slate-50 transition-colors">
                  {headers.slice(0, 4).map(h => (
                    <td key={h} className="px-6 py-4 text-sm text-slate-600 max-w-xs overflow-hidden text-ellipsis whitespace-nowrap">
                      {res.originalRow[h]}
                    </td>
                  ))}
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1.5">
                      {res.matches.length > 0 ? (
                        res.matches.map(m => (
                          <span key={m.termId} className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${isRowMode ? 'bg-indigo-50 text-indigo-800 border-indigo-200' : 'bg-blue-100 text-blue-800 border-blue-200'}`}>
                            {m.termTitle}
                            {!isRowMode && <span className="ml-1.5 opacity-60">×{m.count}</span>}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-slate-300 italic">None found</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-center">
                    {isRowMode ? (
                      <span className={`inline-flex items-center justify-center w-8 h-8 rounded-lg text-sm font-bold ${
                        res.matches.length > 0 ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-400'
                      }`}>
                        {res.matches.length > 0 ? '✓' : '0'}
                      </span>
                    ) : (
                      <span className={`inline-flex items-center justify-center w-8 h-8 rounded-lg text-sm font-bold ${
                        res.totalMatches > 0 ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-400'
                      }`}>
                        {res.totalMatches}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
              {finalResults.length === 0 && (
                <tr>
                  <td colSpan={headers.length + 2} className="px-6 py-12 text-center text-slate-400">
                    No matching records found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ResultsTable;
