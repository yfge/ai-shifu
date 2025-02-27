import React, { createContext, useContext, useState, ReactNode } from "react";
import { Scenario, Chapter, ScenarioContextType } from "../types/scenario";
import api from "@/api";

const ScenarioContext = createContext<ScenarioContextType | undefined>(undefined);

export const ScenarioProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [currentScenario, setCurrentScenario] = useState<Scenario | null>(null);
    const [chapters, setChapters] = useState<Chapter[]>([]);
    const [currentChapter, setCurrentChapter] = useState<Chapter | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const loadScenario = async (scenarioId: string) => {
        try {
            setIsLoading(true);
            setError(null);
            const scenario = await api.getScenario({ scenarioId });
            setCurrentScenario(scenario);
        } catch (error) {
            console.error(error);
            setError("Failed to load scenario");
        } finally {
            setIsLoading(false);
        }
    };

    const loadChapters = async (scenarioId: string) => {
        try {
            setIsLoading(true);
            setError(null);
            const chaptersData = await api.getScenarioChapters({ scenarioId });
            setChapters(chaptersData);
        } catch (error) {
            console.error(error);
            setError("Failed to load chapters");
        } finally {
            setIsLoading(false);
        }
    };

    const saveChapter = async (chapter: Chapter) => {
        try {
            setIsLoading(true);
            setError(null);
            await api.modifyChapter(chapter);
            setChapters(chapters.map(ch =>
                ch.chapter_index === chapter.chapter_index ? chapter : ch
            ));
            if (currentChapter?.chapter_index === chapter.chapter_index) {
                setCurrentChapter(chapter);
            }
        } catch (error) {
            console.error(error);
            setError("Failed to save chapter");
        } finally {
            setIsLoading(false);
        }
    };

    const createChapter = async (chapterData: Omit<Chapter, "chapter_index">) => {
        try {
            setIsLoading(true);
            setError(null);
            const newChapter = await api.createChapter(chapterData);
            setChapters([...chapters, newChapter]);
        } catch (error) {
            console.error(error);
            setError("Failed to create chapter");
        } finally {
            setIsLoading(false);
        }
    };

    const value: ScenarioContextType = {
        currentScenario,
        chapters,
        currentChapter,
        isLoading,
        error,
        actions: {
            loadScenario,
            loadChapters,
            setCurrentChapter,
            saveChapter,
            createChapter,
        },
    };
    // const init = async () => {
    //     // await loadScenario(id);
    //     await loadChapters(id);
    // }
    // useEffect(() => {
    //     init();
    // }, [])

    return <ScenarioContext.Provider value={value}>{children}</ScenarioContext.Provider>;
};

export const useScenario = (): ScenarioContextType => {
    const context = useContext(ScenarioContext);
    if (context === undefined) {
        throw new Error("useScenario must be used within a ScenarioProvider");
    }
    return context;
};
