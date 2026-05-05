import { PresetTemplate, TemplateRenderRequest } from "./types";
import { BEAUTY_ENGINE_V4_TEMPLATES, PRESET_TEMPLATES_MAP } from "./data";

export class PresetLibrary {
  list(industry?: string, engine?: string): PresetTemplate[] {
    return BEAUTY_ENGINE_V4_TEMPLATES.filter((template) => {
      if (industry && template.industry !== industry) return false;
      if (engine && template.engine !== engine) return false;
      return true;
    });
  }

  get(template_id: string): PresetTemplate | null {
    return PRESET_TEMPLATES_MAP.get(template_id) || null;
  }

  compile_prompt(payload: TemplateRenderRequest): {
    template_id: string;
    compiled_prompt: string;
    metadata: Record<string, unknown>;
  } {
    const template = this.get(payload.template_id);
    if (!template) {
      throw new Error(`Template ${payload.template_id} not found`);
    }

    // Simple prompt compilation: replace known placeholders
    let compiled = template.prompt;

    if (payload.brand_name) {
      compiled = compiled.replace(/\{brand_name\}/g, payload.brand_name);
      compiled = compiled.replace(/{{brand_name}}/g, payload.brand_name);
    }

    if (payload.headline) {
      compiled = compiled.replace(/\{headline\}/g, payload.headline);
      compiled = compiled.replace(/{{headline}}/g, payload.headline);
    }

    if (payload.product_name) {
      compiled = compiled.replace(/\{product_name\}/g, payload.product_name);
      compiled = compiled.replace(/{{product_name}}/g, payload.product_name);
    }

    if (payload.extra_notes) {
      compiled += `\n\nEXTRA NOTES:\n${payload.extra_notes}`;
    }

    return {
      template_id: payload.template_id,
      compiled_prompt: compiled,
      metadata: {
        engine: template.engine,
        format: template.format,
        ctr_notes: template.ctr_notes,
        hardlocks: template.qa_hardlock,
        used_fields: {
          brand_name: !!payload.brand_name,
          headline: !!payload.headline,
          cta: !!payload.cta,
          icons: !!payload.icons,
          product_name: !!payload.product_name,
          extra_notes: !!payload.extra_notes,
        },
      },
    };
  }
}
