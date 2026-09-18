// Model picker mock-up. The current backend always answers with its own OpenAI model;
// the chosen id is sent to /ask as `model` so the server can start honouring it later.

export const MODELS = [
  {
    id: 'claude-opus-5',
    name: 'Opus 5',
    provider: 'Anthropic',
    description: 'Most capable, for complex cases',
    pro: true,
  },
  {
    id: 'claude-sonnet-5',
    name: 'Sonnet 5',
    provider: 'Anthropic',
    description: 'Balanced speed and depth',
    pro: false,
  },
  {
    id: 'claude-haiku-4-5',
    name: 'Haiku 4.5',
    provider: 'Anthropic',
    description: 'Fastest, for quick questions',
    pro: false,
  },
  {
    id: 'gpt-5',
    name: 'GPT-5',
    provider: 'OpenAI',
    description: "OpenAI's flagship model",
    pro: false,
  },
];

export const DEFAULT_MODEL_ID = 'claude-sonnet-5';

export const findModel = (id) => MODELS.find((m) => m.id === id) ?? MODELS.find((m) => m.id === DEFAULT_MODEL_ID);
