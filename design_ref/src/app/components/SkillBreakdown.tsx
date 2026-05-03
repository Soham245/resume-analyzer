import { CheckCircle2, XCircle, AlertCircle } from 'lucide-react';

interface Skill {
  name: string;
  status: 'matched' | 'missing' | 'partial';
}

interface SkillBreakdownProps {
  technicalSkills: Skill[];
  softSkills: Skill[];
}

export function SkillBreakdown({ technicalSkills, softSkills }: SkillBreakdownProps) {
  const SkillTag = ({ skill }: { skill: Skill }) => {
    const statusConfig = {
      matched: {
        icon: CheckCircle2,
        bgColor: 'bg-[#e8f0e8]',
        textColor: 'text-[#4a6b4f]',
        iconColor: 'text-[#5a8560]'
      },
      missing: {
        icon: XCircle,
        bgColor: 'bg-[#f5e8e5]',
        textColor: 'text-[#8b4a3f]',
        iconColor: 'text-[#c55a4a]'
      },
      partial: {
        icon: AlertCircle,
        bgColor: 'bg-[#f5ede0]',
        textColor: 'text-[#8b6f47]',
        iconColor: 'text-[#c5935a]'
      }
    };

    const config = statusConfig[skill.status];
    const Icon = config.icon;

    return (
      <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md ${config.bgColor} ${config.textColor}`}>
        <Icon className={`w-3.5 h-3.5 ${config.iconColor}`} />
        <span className="text-sm">{skill.name}</span>
      </div>
    );
  };

  return (
    <div className="bg-card rounded-lg border border-border p-6">
      <h3 className="mb-4">Skill Analysis</h3>

      <div className="space-y-6">
        <div>
          <p className="text-sm text-muted-foreground mb-3">Technical Skills</p>
          <div className="flex flex-wrap gap-2">
            {technicalSkills.map((skill, idx) => (
              <SkillTag key={idx} skill={skill} />
            ))}
          </div>
        </div>

        <div>
          <p className="text-sm text-muted-foreground mb-3">Soft Skills</p>
          <div className="flex flex-wrap gap-2">
            {softSkills.map((skill, idx) => (
              <SkillTag key={idx} skill={skill} />
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 pt-6 border-t border-border flex items-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-[#5a8560]" />
          <span className="text-muted-foreground">Matched</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-[#c5935a]" />
          <span className="text-muted-foreground">Partial</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-[#c55a4a]" />
          <span className="text-muted-foreground">Missing</span>
        </div>
      </div>
    </div>
  );
}
