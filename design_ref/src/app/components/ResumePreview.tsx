interface ResumeSection {
  title: string;
  content: string[];
}

interface ResumePreviewProps {
  sections: ResumeSection[];
}

export function ResumePreview({ sections }: ResumePreviewProps) {
  return (
    <div className="bg-card rounded-lg border border-border p-6">
      <div className="flex items-center justify-between mb-6">
        <h3>Optimized Resume</h3>
        <button className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-opacity">
          Download PDF
        </button>
      </div>

      <div className="bg-white border border-border rounded-lg p-8 space-y-6 max-h-[600px] overflow-y-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
        {sections.map((section, idx) => (
          <div key={idx}>
            <h4 className="text-primary mb-3 pb-2 border-b border-border">{section.title}</h4>
            <div className="space-y-2">
              {section.content.map((item, itemIdx) => (
                <p key={itemIdx} className="text-sm text-foreground leading-relaxed">
                  {item}
                </p>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
