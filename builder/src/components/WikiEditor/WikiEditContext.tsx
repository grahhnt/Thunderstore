import React, { PropsWithChildren, useContext, useState } from "react";
import { MarkdownPreviewProvider } from "./MarkdownPreviewContext";
import { WikiPageUpsertRequest } from "../../api";
import { useOnBeforeUnload } from "../../state/OnBeforeUnload";

export interface IWikiEditContext {
    page: {
        id?: string;
        title: string;
        markdown_content: string;
    };
    package: {
        namespace: string;
        name: string;
    };
    setMarkdown: (markdown: string) => void;
    setTitle: (title: string) => void;
    clearCache: () => void;
}

export interface WikiEditContextProviderProps {
    pkg: {
        namespace: string;
        name: string;
    };
    page: WikiPageUpsertRequest | null;
}

const useStoredState = (
    enabled: boolean,
    storageKey: string,
    defaultVal: string
): [() => string, (val: string) => string, () => void] => {
    if (enabled) {
        return [
            () => {
                return localStorage.getItem(storageKey) ?? defaultVal;
            },
            (val: string) => {
                localStorage.setItem(storageKey, val);
                return val;
            },
            () => localStorage.removeItem(storageKey),
        ];
    } else {
        return [() => defaultVal, (val: string) => val, () => undefined];
    }
};

export const WikiEditContextProvider: React.FC<
    PropsWithChildren<WikiEditContextProviderProps>
> = ({ children, page, pkg }) => {
    const [title, setTitle] = useState<string>(page?.title ?? "");
    const [
        getStoredMarkdown,
        setStoredMarkdown,
        clearStoredMarkdown,
    ] = useStoredState(
        !page,
        "legacy.wikiEditor.newPageMarkdown",
        page?.markdown_content ?? "# New page"
    );
    const [markdown, setMarkdown] = useState<string>(getStoredMarkdown);
    const _setMarkdown = (val: string) => setMarkdown(setStoredMarkdown(val));

    useOnBeforeUnload(!!page && page.markdown_content != markdown);

    return (
        <WikiEditContext.Provider
            value={{
                page: { id: page?.id, title, markdown_content: markdown },
                package: pkg,
                setMarkdown: _setMarkdown,
                clearCache: clearStoredMarkdown,
                setTitle,
            }}
        >
            <MarkdownPreviewProvider markdown={markdown}>
                {children}
            </MarkdownPreviewProvider>
        </WikiEditContext.Provider>
    );
};
export const WikiEditContext = React.createContext<
    IWikiEditContext | undefined
>(undefined);

export const useWikiEditContext = (): IWikiEditContext => {
    return useContext(WikiEditContext)!;
};
