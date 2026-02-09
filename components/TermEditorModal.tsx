
import React, { useState, useEffect } from 'react';
import { SearchExpression } from '../types';

interface TermEditorModalProps {
  term: SearchExpression | null; // null means create new
  onSave: (term: SearchExpression) => void;
  onClose: () => void;
  onDelete?: (id: string) => void;
}

const TermEditorModal: React.FC<TermEditorModalProps> = ({ term, onSave, onClose, onDelete }) => {
  const [formData, setFormData] = useState<SearchExpression>({
    id: `TERM_${Date.now()}`,
    title_en: '',
    variants_en: [],
    variants_he: [],
    regex_en: '',
    regex_he: '',
    enabled: true
  });

  useEffect(() => {
    if (term) {
      setFormData({ ...term });
    }
  }, [term]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
        <form onSubmit={handleSubmit}>
          <div className="px-8 py-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
            <div>
              <h3 className="text-xl font-bold text-slate-800">{term ? 'Edit Expression' : 'New Expression'}</h3>
              <p className="text-sm text-slate-500">Configure linguistic patterns for extraction</p>
            </div>
            <button type="button" onClick={onClose} className="p-2 hover:bg-slate-200 rounded-full text-slate-400 transition-colors">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>

          <div className="px-8 py-8 space-y-6 max-h-[70vh] overflow-y-auto">
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-2">Term Title (Internal)</label>
              <input 
                type="text" 
                required
                className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                value={formData.title_en}
                onChange={(e) => setFormData({...formData, title_en: e.target.value})}
                placeholder="e.g. Colonialism"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="p-4 bg-blue-50/50 rounded-xl border border-blue-100">
                  <h4 className="text-sm font-bold text-blue-800 mb-3 flex items-center uppercase tracking-wider">
                    <span className="mr-2">🇺🇸</span> English Pattern
                  </h4>
                  <label className="block text-xs font-semibold text-blue-600 mb-1">Regex Pattern</label>
                  <textarea 
                    rows={3}
                    className="w-full px-3 py-2 text-sm mono border border-blue-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                    value={formData.regex_en}
                    onChange={(e) => setFormData({...formData, regex_en: e.target.value})}
                    placeholder="(?i)\\bword\\b"
                  />
                  <p className="text-[10px] text-blue-400 mt-2">Start with (?i) for case-insensitive matching</p>
                </div>
              </div>

              <div className="space-y-4">
                <div className="p-4 bg-indigo-50/50 rounded-xl border border-indigo-100">
                  <h4 className="text-sm font-bold text-indigo-800 mb-3 flex items-center uppercase tracking-wider">
                    <span className="mr-2">🇮🇱</span> Hebrew Pattern
                  </h4>
                  <label className="block text-xs font-semibold text-indigo-600 mb-1">Regex Pattern</label>
                  <textarea 
                    rows={3}
                    dir="rtl"
                    className="w-full px-3 py-2 text-sm mono border border-indigo-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                    value={formData.regex_he}
                    onChange={(e) => setFormData({...formData, regex_he: e.target.value})}
                    placeholder="([ובהכשלו]|^)מילה"
                  />
                  <p className="text-[10px] text-indigo-400 mt-2 text-right">Hebrew prefixes are recommended</p>
                </div>
              </div>
            </div>
          </div>

          <div className="px-8 py-6 bg-slate-50 border-t border-slate-100 flex justify-between items-center">
            {term && onDelete ? (
              <button 
                type="button" 
                onClick={() => onDelete(formData.id)}
                className="text-red-500 hover:text-red-700 text-sm font-bold flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                Delete
              </button>
            ) : <div></div>}
            
            <div className="flex gap-3">
              <button 
                type="button" 
                onClick={onClose}
                className="px-6 py-2 text-slate-600 font-bold hover:bg-slate-200 rounded-lg transition-all"
              >
                Cancel
              </button>
              <button 
                type="submit"
                className="px-8 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg shadow-md transition-all active:scale-95"
              >
                Save Expression
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default TermEditorModal;
