import React, { useEffect, useRef, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/Collapsible';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { useShifu } from '@/store';
import CMEditor, { getProfileKeyListFromContent } from '@/components/cm-editor';
import ModelList from '@/components/model-list';
import api from '@/api';
import {
  ChevronDown,
  ChevronUp,
  Copy,
  Minus,
  Plus,
  Trash2,
} from 'lucide-react';

import { useUserStore } from '@/store';
import { v4 as uuidv4 } from 'uuid';
import Loading from '../loading';
import { useTranslation } from 'react-i18next';
import { ContentDTO } from '@/types/shifu';
import { environment } from '@/config/environment';

async function* makeTextSteamLineIterator(reader: ReadableStreamDefaultReader) {
  const utf8Decoder = new TextDecoder('utf-8');
  // let response = await fetch(fileURL);
  // let reader = response.body.getReader();
  let { value: chunk, done: readerDone } = await reader.read();
  chunk = chunk ? utf8Decoder.decode(chunk, { stream: true }) : '';

  const re = /\r\n|\n|\r/gm;
  let startIndex = 0;

  for (;;) {
    // eslint-disable-next-line prefer-const
    let result = re.exec(chunk);
    if (!result) {
      if (readerDone) {
        break;
      }
      const remainder = chunk.substring(startIndex);
      ({ value: chunk, done: readerDone } = await reader.read());
      chunk =
        remainder + (chunk ? utf8Decoder.decode(chunk, { stream: true }) : '');
      startIndex = re.lastIndex = 0;
      continue;
    }
    yield chunk.substring(startIndex, result.index);
    startIndex = re.lastIndex;
  }
  if (startIndex < chunk.length) {
    // last line didn't end in a newline char
    yield chunk.substr(startIndex);
  }
}

const AIModelDialog = ({ blockId, open, onOpenChange }) => {
  console.log('AIModelDialog', blockId);
  const { t } = useTranslation();
  const SITE_HOST = environment.apiBaseUrl;
  const { getToken } = useUserStore();
  const {
    blockProperties,
    blocks,
    actions,
    // profileItemDefinations
  } = useShifu();
  const [systemPrompt, setSystemPrompt] = useState('');
  const [userPrompt, setUserPrompt] = useState('');
  const [systemPromptOpen, setSystemPromptOpen] = useState(false);
  const [userPromptOpen, setUserPromptOpen] = useState(true);
  const [colCount, setColCount] = useState(2);
  const [rowCount, setRowCount] = useState(300);
  const [profiles, setProfiles] = useState<string[]>([]);
  // const [model, setModel] = useState('');
  const [models, setModels] = useState<
    { model: string; temperature: number }[]
  >([{ model: 'gpt-4o-mini', temperature: 0.7 }]);
  const [results, setResults] = useState<string[]>([]);
  const [runing, setRuning] = useState(false);
  const abortRefs = useRef<AbortController[]>([]);

  const [variables, setVariables] = useState({});
  const init = async () => {
    const block = blocks.find(item => item.bid === blockId);
    if (block) {
      const sysPrompt = await api.getSystemPrompt({
        block_id: blockId,
      });
      setSystemPrompt(sysPrompt);
      const contentProp = block.properties as ContentDTO;
      if (contentProp.llm_enabled == false) {
        setUserPrompt(contentProp.content);
      } else if (contentProp.llm_enabled == true) {
        setUserPrompt(contentProp.content);
        setProfiles(block.variable_bids || []);
        setModels([
          {
            model: contentProp.llm,
            temperature: contentProp.llm_temperature,
          },
        ]);
      }
    }
  };
  const abort = async () => {
    abortRefs.current.forEach(controller => {
      if (controller) {
        controller.abort();
      }
    });
  };
  const onOpenChangeHandle = open => {
    onOpenChange(open);
  };
  const fetchStream = async (
    url: string,
    data: any,
    index: number,
    rowIndex: number,
  ) => {
    try {
      const controller = new AbortController();
      abortRefs.current[rowIndex * colCount + index] = controller;
      const token = getToken();
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
          Token: token,
          'X-Request-ID': uuidv4().replace(/-/g, ''),
        },
        body: JSON.stringify(data),
        signal: controller.signal,
      });

      if (!response.body) {
        throw new Error('No response body');
      }

      const reader = response.body.getReader();

      const lines: string[] = [];
      for await (const line of makeTextSteamLineIterator(reader)) {
        if (!(line as string).startsWith('data:')) {
          continue;
        }
        lines.push(line);
        if (!line || line.includes('[DONE]')) {
          continue;
        }
        const json: any = line.replace(/^data:/, '');
        const data = JSON.parse(json);
        if (data.type === 'text') {
          const position = rowIndex * colCount + index;
          setResults(prev => {
            const newResults = [...prev];
            newResults[position] = newResults[position] + data.content;
            return newResults;
          });
        } else if (data.type === 'text_end') {
        }
      }
    } catch (error) {
      console.error('Error in fetchStream:', error);
      throw error;
    }
  };
  const onDebug = async () => {
    if (runing) {
      await abort();
      setRuning(false);
      return;
    }
    setResults([]);

    const totalResults = models.length * colCount;
    setResults(new Array(totalResults).fill(''));
    abortRefs.current = new Array(totalResults).fill(null);
    setRuning(true);
    for (let i = 0; i < models.length; i++) {
      const { model, temperature } = models[i];

      const promises = Array.from({ length: colCount }, (_, colIndex) =>
        fetchStream(
          `${SITE_HOST}/api/llm/debug-prompt`,
          {
            block_id: blockId,
            block_model: model,
            block_other_conf: {},
            block_prompt: userPrompt,
            block_system_prompt: systemPrompt,
            block_temperature: temperature,
            block_variables: variables,
          },
          colIndex,
          i,
        ),
      );

      await Promise.all(promises);
    }
    setRuning(false);
  };
  const onCopy = (index: number) => {
    const model = models[index];
    setModels([...models, model]);
  };
  const setModel = (index: number, model: string) => {
    const newModels = [...models];
    newModels[index] = {
      ...newModels[index],
      model: model,
    };
    setModels(newModels);
  };
  const setTemperature = (index: number, temperature: number) => {
    const newModels = [...models];
    newModels[index] = {
      ...newModels[index],
      temperature: temperature,
    };
    setModels(newModels);
  };
  const onRemove = (index: number) => {
    const newModels = [...models];
    newModels.splice(index, 1);
    setModels(newModels);
  };
  const onProfileValue = (name: string, value: string) => {
    setVariables(state => {
      return {
        ...state,
        [name]: value,
      };
    });
  };
  const updateBlock = async () => {
    console.log('updateBlock', blockProperties[blockId].properties);
    console.log('updateBlock', userPrompt);
    console.log('updateBlock', models[0].model);
    console.log('updateBlock', models[0].temperature);
    actions.updateBlockProperties(blockId, {
      ...blockProperties[blockId],
      properties: {
        content: userPrompt,
        llm_enabled: true,
        llm: models[0].model,
        llm_temperature: models[0].temperature,
      },
    });
    onOpenChange(false);
  };

  useEffect(() => {
    init();
  }, []);
  useEffect(() => {
    setProfiles(
      Array.from(
        new Set([
          ...getProfileKeyListFromContent(systemPrompt),
          ...getProfileKeyListFromContent(userPrompt),
        ]),
      ),
    );
  }, [systemPrompt, userPrompt]);
  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChangeHandle}
    >
      <DialogContent className='flex flex-col sm:max-w-[600px] md:max-w-[800px] max-h-[90vh] overflow-y-auto text-sm'>
        <div className='absolute right-4 top-4 cursor-pointer'>
          <XMarkIcon
            className='h-4 w-4'
            onClick={() => onOpenChange(false)}
          />
        </div>
        <DialogHeader className='text-center'>
          <DialogTitle className='text-xl font-bold px-2'>
            {t('module.aiDebug.debug')}
          </DialogTitle>
        </DialogHeader>
        <div className=' flex-1 space-y-4 overflow-auto px-4'>
          <div className='text-sm font-medium'>
            {t('module.aiDebug.aiModuleContent')}
          </div>
          <Collapsible
            open={systemPromptOpen}
            onOpenChange={setSystemPromptOpen}
            className='w-full border rounded-xl bg-gray-50'
          >
            <CollapsibleTrigger className='flex justify-between items-center w-full p-3'>
              <span className='text-gray-500'>
                {t('module.aiDebug.systemPrompt')}
              </span>
              <div className='flex items-center'>
                <span className='mr-2 text-gray-500'>
                  {systemPromptOpen
                    ? t('module.aiDebug.collapse')
                    : t('module.aiDebug.expand')}
                </span>
                {systemPromptOpen ? (
                  <ChevronDown className='h-4 w-4' />
                ) : (
                  <ChevronUp className='h-4 w-4' />
                )}
              </div>
            </CollapsibleTrigger>
            <CollapsibleContent className='p-0'>
              <CMEditor
                content={systemPrompt}
                onChange={setSystemPrompt}
                isEdit={true}
              ></CMEditor>
            </CollapsibleContent>
          </Collapsible>
          <Collapsible
            open={userPromptOpen}
            onOpenChange={setUserPromptOpen}
            className='w-full border rounded-xl bg-gray-50'
          >
            <CollapsibleTrigger className='flex justify-between items-center w-full p-3'>
              <span className='text-gray-500'>
                {t('module.aiDebug.userPrompt')}
              </span>
              <div className='flex items-center'>
                <span className='mr-2 text-gray-500'>
                  {userPromptOpen
                    ? t('module.aiDebug.collapse')
                    : t('module.aiDebug.expand')}
                </span>
                {userPromptOpen ? (
                  <ChevronUp className='h-4 w-4' />
                ) : (
                  <ChevronDown className='h-4 w-4' />
                )}
              </div>
            </CollapsibleTrigger>
            <CollapsibleContent className='py-2 overflow-hidden'>
              <CMEditor
                content={userPrompt}
                onChange={setUserPrompt}
                isEdit={true}
              ></CMEditor>
              <div className='flex flex-row justify-end px-2'>
                <Button
                  variant='ghost'
                  className='px-2 h-6 text-primary cursor-pointer'
                  onClick={updateBlock}
                >
                  {t('module.aiDebug.updateToShifu')}
                </Button>
              </div>
            </CollapsibleContent>
          </Collapsible>
          <div className='flex flex-col gap-2'>
            <div className='grid grid-cols-2 gap-4'>
              <div>
                <div className='mb-1 text-sm'>
                  {t('common.core.selectModel')}
                </div>
              </div>

              <div>
                <div className='mb-1 text-sm'>
                  {t('module.aiDebug.setTemperature')}
                </div>
              </div>
            </div>
            {models?.map((model, i) => {
              return (
                <div
                  key={model.model + i}
                  className='grid grid-cols-2 gap-4'
                >
                  <ModelList
                    className='h-8'
                    value={model.model}
                    onChange={setModel.bind(null, i)}
                  />
                  <div className='flex items-center space-x-2'>
                    <Input
                      type='text'
                      value={model.temperature}
                      onChange={e =>
                        setTemperature(i, parseFloat(e.target.value))
                      }
                      // step="0.1"
                      // min="0"
                      // max="1"
                      className='w-full'
                    />
                    <Button
                      variant='outline'
                      size='icon'
                      disabled={model.temperature <= 0}
                      className='h-8 w-8 shrink-0'
                      onClick={() => {
                        const val = Number(model.temperature);
                        if (val <= 0) {
                          setTemperature(i, 0);
                          return;
                        }
                        setTemperature(i, Number((val - 0.1).toFixed(1)));
                      }}
                    >
                      <Minus className='h-4 w-4' />
                    </Button>
                    <Button
                      variant='outline'
                      size='icon'
                      disabled={model.temperature >= 1}
                      className='h-8 w-8 shrink-0'
                      onClick={() => {
                        const val = Number(model.temperature);
                        if (val >= 1) {
                          setTemperature(i, 1);
                          return;
                        }
                        setTemperature(i, Number((val + 0.1).toFixed(1)));
                      }}
                    >
                      <Plus className='h-4 w-4' />
                    </Button>
                    <Button
                      variant='outline'
                      size='icon'
                      className='h-8 w-8 shrink-0'
                      onClick={onRemove.bind(null, i)}
                    >
                      <Trash2 className='h-4 w-4' />
                    </Button>
                    <Button
                      variant='outline'
                      size='icon'
                      className='h-8 w-8 shrink-0'
                      onClick={onCopy.bind(null, i)}
                    >
                      <Copy className='h-4 w-4' />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
          <div>
            {profiles?.map(item => {
              return (
                <div
                  key={item}
                  className='grid grid-cols-2 gap-4'
                >
                  <div>
                    <div className='mb-1 text-sm'>
                      {t('module.aiDebug.variable')}
                    </div>
                    <Input
                      value={item}
                      readOnly
                    />
                  </div>
                  <div>
                    <div className='mb-1 text-sm'>
                      {t('module.aiDebug.inputVariableValue')}
                    </div>
                    <Input
                      onChange={e => onProfileValue(item, e.target.value)}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          <div className='grid grid-cols-2 gap-4'>
            <div>
              <div className='mb-1 text-sm'>
                {t('module.aiDebug.columnCount')}
              </div>
              <div className='flex items-center space-x-2'>
                <Input
                  type='text'
                  value={colCount}
                  onChange={e => setColCount(parseInt(e.target.value))}
                  className='w-full'
                />
                <Button
                  variant='outline'
                  size='icon'
                  className='h-8 w-8 shrink-0'
                  onClick={() => {
                    if (colCount <= 1) {
                      setColCount(1);
                      return;
                    }
                    setColCount(colCount - 1);
                  }}
                >
                  <Minus className='h-4 w-4' />
                </Button>
                <Button
                  variant='outline'
                  size='icon'
                  className='h-8 w-8 shrink-0'
                  onClick={() => {
                    setColCount(colCount + 1);
                  }}
                >
                  <Plus className='h-4 w-4' />
                </Button>
              </div>
            </div>
            <div>
              <div className='mb-1 text-sm'>{t('module.aiDebug.rowCount')}</div>
              <div className='flex items-center space-x-2'>
                <Input
                  type='text'
                  value={rowCount}
                  onChange={e => setRowCount(parseInt(e.target.value))}
                  className='w-full'
                />
              </div>
            </div>
          </div>

          <div className='mt-6 flex justify-center'>
            <Button
              className='bg-primary hover:bg-primary-lighter text-white w-full'
              onClick={onDebug}
            >
              {!runing && <span>{t('module.aiDebug.startDebug')}</span>}
              {runing && (
                <span className='flex flex-row items-center'>
                  <Loading className='h-4 w-4 animate-spin mr-1' />
                  {t('module.aiDebug.stopOutput')}
                </span>
              )}
            </Button>
          </div>
          <div className='flex flex-col gap-4'>
            {models?.map((model, modelIndex) => (
              <div
                key={model.model + modelIndex}
                className='space-y-2'
              >
                <div
                  className='grid gap-4'
                  style={{
                    gridTemplateColumns: `repeat(${colCount}, 1fr)`,
                  }}
                >
                  {results
                    .slice(modelIndex * colCount, (modelIndex + 1) * colCount)
                    .map((item, i) => (
                      <div
                        key={i}
                        className='flex flex-col space-y-2 bg-[#F5F5F4] rounded-md p-3 whitespace-pre-wrap'
                      >
                        <div className='text-sm text-gray-500'>
                          {' '}
                          {model.model}, {model.temperature}
                        </div>
                        <div>{item}</div>
                      </div>
                    ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default AIModelDialog;
