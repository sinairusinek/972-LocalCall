
import React from 'react';
import { SearchMode, SearchExpression, AnalysisOptions, AnalysisCountMode } from '../types';

interface ConfigurationProps {
  headers: string[];
  selectedColumns: string[];
  expressions: SearchExpression[];
  analysisOptions: AnalysisOptions;
  onToggleColumn: (header: string) => void;
  onToggleExpression: (id: string) => void;
  onSetAnalysisOptions: (options: AnalysisOptions) => void;
  onRunAnalysis: () => void;
  onEditExpression: (term: SearchExpression) => void;
  onAddNewExpression: () => void;
  onBulkExpressions: (type: 'ALL' | 'NONE' | 'ENGLISH' | 'HEBREW') => void;
}

const Configuration: React.FC<ConfigurationProps> = ({
  headers,
  selectedColumns,
  expressions,
  analysisOptions,
  onToggleColumn,
  onToggleExpression,
  onSetAnalysisOptions,
  onRunAnalysis,
  onEditExpression,
  onAddNewExpression,
  onBulkExpressions
}) => {
  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1 space-y-8">
          {/* Step 1: Columns */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
            <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center">
              <span className="w-8 h-8 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center mr-3 text-xs">1</span>
              Corpus Fields
            </h3>
            <div className="space-y-2">
              {headers.map(header => (
                <label 
                  key={header} 
                  className={`flex items-center p-2.5 rounded-xl border transition-all cursor-pointer ${
                    selectedColumns.includes(header) 
                      ? 'bg-blue-50 border-blue-200 text-blue-700 shadow-sm' 
                      : 'bg-slate-50 border-slate-100 text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  <input 
                    type="checkbox" 
                    className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 mr-3"
                    checked={selectedColumns.includes(header)}
                    onChange={() => onToggleColumn(header)}
                  />
                  <span className="truncate text-sm font-medium">{header}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Step 2: Logic */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
            <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center">
              <span className="w-8 h-8 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center mr-3 text-xs">2</span>
              Search Scope & Logic
            </h3>
            <div className="space-y-6">
              <div className="space-y-3">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Search Mode</span>
                <div className="grid grid-cols-2 gap-2">
                  <label className={`flex flex-col items-center p-3 rounded-xl border transition-all cursor-pointer ${
                    analysisOptions.mode === SearchMode.CONCATENATED ? 'bg-blue-50 border-blue-200' : 'bg-slate-50 border-slate-100'
                  }`}>
                    <input 
                      type="radio" 
                      className="hidden"
                      checked={analysisOptions.mode === SearchMode.CONCATENATED}
                      onChange={() => onSetAnalysisOptions({...analysisOptions, mode: SearchMode.CONCATENATED})}
                    />
                    <span className="text-sm font-bold text-slate-800">Joint</span>
                    <p className="text-[9px] text-slate-500 text-center">Full row text</p>
                  </label>
                  <label className={`flex flex-col items-center p-3 rounded-xl border transition-all cursor-pointer ${
                    analysisOptions.mode === SearchMode.SEPARATE ? 'bg-blue-50 border-blue-200' : 'bg-slate-50 border-slate-100'
                  }`}>
                    <input 
                      type="radio" 
                      className="hidden"
                      checked={analysisOptions.mode === SearchMode.SEPARATE}
                      onChange={() => onSetAnalysisOptions({...analysisOptions, mode: SearchMode.SEPARATE})}
                    />
                    <span className="text-sm font-bold text-slate-800">Per Cell</span>
                    <p className="text-[9px] text-slate-500 text-center">Field-by-field</p>
                  </label>
                </div>
              </div>

              <div className="space-y-3 border-t border-slate-100 pt-4">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Aggregation Mode</span>
                <div className="grid grid-cols-2 gap-2">
                  <label className={`flex flex-col items-center p-3 rounded-xl border transition-all cursor-pointer ${
                    analysisOptions.countMode === AnalysisCountMode.HITS ? 'bg-indigo-50 border-indigo-200' : 'bg-slate-50 border-slate-100'
                  }`}>
                    <input 
                      type="radio" 
                      className="hidden"
                      checked={analysisOptions.countMode === AnalysisCountMode.HITS}
                      onChange={() => onSetAnalysisOptions({...analysisOptions, countMode: AnalysisCountMode.HITS})}
                    />
                    <span className="text-sm font-bold text-slate-800 text-center">Occurrences</span>
                    <p className="text-[9px] text-slate-500 text-center">Count every hit</p>
                  </label>
                  <label className={`flex flex-col items-center p-3 rounded-xl border transition-all cursor-pointer ${
                    analysisOptions.countMode === AnalysisCountMode.ROWS ? 'bg-indigo-50 border-indigo-200' : 'bg-slate-50 border-slate-100'
                  }`}>
                    <input 
                      type="radio" 
                      className="hidden"
                      checked={analysisOptions.countMode === AnalysisCountMode.ROWS}
                      onChange={() => onSetAnalysisOptions({...analysisOptions, countMode: AnalysisCountMode.ROWS})}
                    />
                    <span className="text-sm font-bold text-slate-800 text-center">Unique Posts</span>
                    <p className="text-[9px] text-slate-500 text-center">Count rows only</p>
                  </label>
                </div>
              </div>

              <div className="space-y-4 border-t border-slate-100 pt-4">
                <div className="space-y-1">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Timeline Column</span>
                  <select 
                    className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                    value={analysisOptions.dateColumn || ''}
                    onChange={(e) => onSetAnalysisOptions({...analysisOptions, dateColumn: e.target.value || undefined})}
                  >
                    <option value="">None (Disable Timeline)</option>
                    {headers.map(h => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>
                
                <div className="space-y-1">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Author Column</span>
                  <select 
                    className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
                    value={analysisOptions.authorColumn || ''}
                    onChange={(e) => onSetAnalysisOptions({...analysisOptions, authorColumn: e.target.value || undefined})}
                  >
                    <option value="">None (Disable Author Filter)</option>
                    {headers.map(h => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                  <p className="text-[9px] text-slate-400 italic">Values can be separated by | (e.g. Author1 | Author2)</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Step 3: Terms Library */}
        <div className="lg:col-span-2 space-y-8">
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex flex-col h-full">
            <div className="flex justify-between items-start mb-6">
              <h3 className="text-lg font-bold text-slate-800 flex items-center">
                <span className="w-8 h-8 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center mr-3 text-xs">3</span>
                Terms Library
              </h3>
              <button 
                onClick={onAddNewExpression}
                className="text-xs font-bold text-blue-600 hover:text-blue-700 bg-blue-50 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                Add New
              </button>
            </div>

            <div className="flex flex-wrap gap-2 mb-6 p-3 bg-slate-50 rounded-xl border border-slate-100">
              <div className="w-full text-[10px] uppercase font-bold text-slate-400 mb-2 tracking-widest px-1">Language Filters (Active Patterns)</div>
              <label className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border cursor-pointer transition-all ${
                analysisOptions.includeEnglish ? 'bg-blue-600 border-blue-600 text-white shadow-md' : 'bg-white border-slate-200 text-slate-600'
              }`}>
                <input 
                  type="checkbox" 
                  className="hidden"
                  checked={analysisOptions.includeEnglish}
                  onChange={() => onSetAnalysisOptions({...analysisOptions, includeEnglish: !analysisOptions.includeEnglish})}
                />
                <span className="text-xs font-bold">🇺🇸 English Patterns</span>
              </label>
              <label className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border cursor-pointer transition-all ${
                analysisOptions.includeHebrew ? 'bg-indigo-600 border-indigo-600 text-white shadow-md' : 'bg-white border-slate-200 text-slate-600'
              }`}>
                <input 
                  type="checkbox" 
                  className="hidden"
                  checked={analysisOptions.includeHebrew}
                  onChange={() => onSetAnalysisOptions({...analysisOptions, includeHebrew: !analysisOptions.includeHebrew})}
                />
                <span className="text-xs font-bold">🇮🇱 Hebrew Patterns</span>
              </label>

              <div className="w-full border-t border-slate-200 my-2"></div>
              
              <div className="w-full text-[10px] uppercase font-bold text-slate-400 mb-2 tracking-widest px-1">Selection Presets</div>
              <button onClick={() => onBulkExpressions('ALL')} className="text-[11px] font-bold px-3 py-1 bg-slate-200 text-slate-700 rounded-md hover:bg-slate-300">All</button>
              <button onClick={() => onBulkExpressions('NONE')} className="text-[11px] font-bold px-3 py-1 bg-slate-200 text-slate-700 rounded-md hover:bg-slate-300">None</button>
              <button onClick={() => onBulkExpressions('ENGLISH')} className="text-[11px] font-bold px-3 py-1 bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200">Only English</button>
              <button onClick={() => onBulkExpressions('HEBREW')} className="text-[11px] font-bold px-3 py-1 bg-indigo-100 text-indigo-700 rounded-md hover:bg-indigo-200">Only Hebrew</button>
            </div>

            <div className="overflow-y-auto max-h-[400px] border border-slate-100 rounded-xl">
              <table className="w-full text-left border-collapse">
                <thead className="sticky top-0 bg-white shadow-sm z-10">
                  <tr>
                    <th className="p-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Use</th>
                    <th className="p-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Expression</th>
                    <th className="p-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Scope</th>
                    <th className="p-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {expressions.map(exp => (
                    <tr key={exp.id} className={`group hover:bg-slate-50 transition-colors ${exp.enabled === false ? 'opacity-50' : ''}`}>
                      <td className="p-3">
                        <input 
                          type="checkbox" 
                          className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500"
                          checked={exp.enabled !== false}
                          onChange={() => onToggleExpression(exp.id)}
                        />
                      </td>
                      <td className="p-3">
                        <span className="text-sm font-bold text-slate-800 block truncate max-w-[150px]">{exp.title_en}</span>
                      </td>
                      <td className="p-3">
                        <div className="flex gap-1">
                          {exp.regex_en && <span className="text-[9px] px-1 bg-blue-100 text-blue-700 rounded font-bold">EN</span>}
                          {exp.regex_he && <span className="text-[9px] px-1 bg-indigo-100 text-indigo-700 rounded font-bold">HE</span>}
                        </div>
                      </td>
                      <td className="p-3 text-right">
                        <button 
                          onClick={() => onEditExpression(exp)}
                          className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-center pt-8 border-t border-slate-100">
        <button 
          onClick={onRunAnalysis}
          disabled={selectedColumns.length === 0 || expressions.filter(e => e.enabled !== false).length === 0}
          className={`group flex items-center gap-4 px-12 py-5 rounded-2xl font-bold shadow-xl transition-all transform active:scale-95 ${
            selectedColumns.length > 0 && expressions.filter(e => e.enabled !== false).length > 0
              ? 'bg-blue-600 hover:bg-blue-700 text-white hover:translate-y-[-2px]' 
              : 'bg-slate-200 text-slate-400 cursor-not-allowed'
          }`}
        >
          <span>Run Analysis</span>
          <div className="flex flex-col items-start border-l border-white/20 pl-4">
            <span className="text-xs opacity-80 uppercase tracking-tighter">Selected</span>
            <span className="text-sm">{expressions.filter(e => e.enabled !== false).length} terms</span>
          </div>
        </button>
      </div>
    </div>
  );
};

export default Configuration;
