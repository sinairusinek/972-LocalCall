
import React from 'react';
import { Icons } from '../constants';

interface FileUploadProps {
  onDataLoaded: (data: any[]) => void;
  isLoading: boolean;
}

const FileUpload: React.FC<FileUploadProps> = ({ onDataLoaded, isLoading }) => {
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      // We'll pass the text back to App to be parsed
      onDataLoaded([{ _raw: text }]); 
    };
    reader.readAsText(file);
  };

  return (
    <div className="max-w-xl mx-auto mt-12">
      <div className="bg-white rounded-2xl shadow-sm border-2 border-dashed border-slate-200 p-12 text-center hover:border-blue-400 transition-colors">
        <div className="flex justify-center mb-6">
          <div className="bg-blue-50 p-4 rounded-full text-blue-600">
            <Icons.Upload />
          </div>
        </div>
        <h3 className="text-xl font-semibold text-slate-800 mb-2">Upload Corpus</h3>
        <p className="text-slate-500 mb-8">Select a .tsv file containing your textual corpus data.</p>
        
        <label className="inline-flex items-center px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg cursor-pointer transition-all shadow-md active:scale-95">
          <span>{isLoading ? 'Processing...' : 'Choose File'}</span>
          <input 
            type="file" 
            accept=".tsv,.txt" 
            className="hidden" 
            onChange={handleFileChange} 
            disabled={isLoading}
          />
        </label>
        
        <div className="mt-8 text-xs text-slate-400">
          Supported format: Tab-Separated Values (.tsv)
        </div>
      </div>
    </div>
  );
};

export default FileUpload;
