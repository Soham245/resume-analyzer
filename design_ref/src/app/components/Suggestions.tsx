import { Lightbulb } from 'lucide-react';

interface SuggestionsProps {
  suggestions: string[];
}

export function Suggestions({ suggestions }: SuggestionsProps) {
  return (
    <div className="bg-card rounded-lg border border-border p-6">
      <div className="flex items-center gap-2 mb-4">
        <Lightbulb className="w-5 h-5 text-primary" />
        <h3>Recommendations</h3>
      </div>

      <div className="space-y-3">
        {suggestions.map((suggestion, idx) => (
          <div key={idx} className="flex gap-3">
            <div className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-primary mt-2" />
            <p className="text-sm text-foreground leading-relaxed">{suggestion}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
