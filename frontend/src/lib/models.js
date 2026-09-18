// Model picker. GPT-5 is the default for everyone; Claude is part of Pro.
// The server still answers with its own OpenAI model; the chosen id is sent to /ask as `model`.

export const MODELS = [
  {
    id: 'gpt-5',
    name: 'GPT-5',
    provider: 'OpenAI',
    description: 'Default model, fast and reliable',
    pro: false,
  },
  {
    id: 'claude-opus-5',
    name: 'Claude',
    provider: 'Anthropic',
    description: 'Opus 5, most capable for complex cases',
    pro: true,
  },
];

export const DEFAULT_MODEL_ID = 'gpt-5';

// Unknown ids (e.g. Sonnet or Haiku saved before the list was shortened) fall back to the default
export const findModel = (id) => MODELS.find((m) => m.id === id) ?? MODELS.find((m) => m.id === DEFAULT_MODEL_ID);
