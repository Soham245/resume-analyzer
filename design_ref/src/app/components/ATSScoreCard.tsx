import { TrendingUp, TrendingDown } from 'lucide-react';

interface ATSScoreCardProps {
  score: number;
  improvement: number;
  confidence: number;
}

export function ATSScoreCard({ score, improvement, confidence }: ATSScoreCardProps) {
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-[var(--success)]';
    if (score >= 60) return 'text-[var(--warning)]';
    return 'text-destructive';
  };

  const getScoreBg = (score: number) => {
    if (score >= 80) return 'bg-[#e8f0e8]';
    if (score >= 60) return 'bg-[#f5ede0]';
    return 'bg-[#f5e8e5]';
  };

  return (
    <div className={`rounded-lg border border-border p-6 ${getScoreBg(score)}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-muted-foreground mb-2">ATS Compatibility Score</p>
          <div className="flex items-baseline gap-3">
            <h1 className={`text-5xl ${getScoreColor(score)}`}>{score}</h1>
            <span className="text-2xl text-muted-foreground">/100</span>
          </div>
        </div>

        <div className="text-right">
          <div className={`flex items-center gap-1 text-sm ${improvement >= 0 ? 'text-[var(--success)]' : 'text-destructive'}`}>
            {improvement >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
            <span>{Math.abs(improvement)}% potential improvement</span>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {confidence}% confidence
          </p>
        </div>
      </div>

      <div className="mt-4 h-2 bg-white/50 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-700 ${
            score >= 80 ? 'bg-[var(--success)]' :
            score >= 60 ? 'bg-[var(--warning)]' :
            'bg-destructive'
          }`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}
