import { FileSearch } from 'lucide-react';

export function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="w-16 h-16 rounded-full bg-accent flex items-center justify-center mb-4">
        <FileSearch className="w-8 h-8 text-accent-foreground" />
      </div>
      <h3 className="text-foreground mb-2">Ready to analyze</h3>
      <p className="text-sm text-muted-foreground text-center max-w-md">
        Upload your resume and paste a job description to see your ATS score, identify skill gaps, and get personalized recommendations
      </p>
    </div>
  );
}
