import { create } from "zustand";

export type ElementType = "text" | "image" | "shape" | "background";

export interface DesignElement {
  id: string;
  type: ElementType;
  x: number;
  y: number;
  width: number;
  height: number;
  content?: string;
  src?: string;
  style?: Record<string, string | number>;
}

export interface DesignDoc {
  id: string;
  name: string;
  elements: DesignElement[];
}

interface EditorState {
  doc: DesignDoc;
  selectedId: string | null;
  setDoc: (doc: DesignDoc) => void;
  selectElement: (id: string | null) => void;
  updateElement: (id: string, changes: Partial<DesignElement>) => void;
  addElement: (el: DesignElement) => void;
  removeElement: (id: string) => void;
}

const defaultDoc: DesignDoc = {
  id: "default",
  name: "Untitled",
  elements: []
};

export const useEditorStore = create<EditorState>((set) => ({
  doc: defaultDoc,
  selectedId: null,

  setDoc: (doc) => set({ doc }),

  selectElement: (id) => set({ selectedId: id }),

  updateElement: (id, changes) =>
    set((state) => ({
      doc: {
        ...state.doc,
        elements: state.doc.elements.map((el) =>
          el.id === id ? { ...el, ...changes } : el
        )
      }
    })),

  addElement: (el) =>
    set((state) => ({
      doc: {
        ...state.doc,
        elements: [...state.doc.elements, el]
      }
    })),

  removeElement: (id) =>
    set((state) => ({
      doc: {
        ...state.doc,
        elements: state.doc.elements.filter((el) => el.id !== id)
      }
    }))
}));
