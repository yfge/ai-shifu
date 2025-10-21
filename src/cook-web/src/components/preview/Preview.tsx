import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from '@/components/ui/Dialog';
import { Button } from '@/components/button';
import { Switch } from '@/components/ui/Switch';
import { PlayIcon } from 'lucide-react';
import { useShifu } from '@/store';
import api from '@/api';
import { useAlert } from '@/components/ui/UseAlert';
import { useTranslation } from 'react-i18next';

const PreviewSettingsModal = () => {
  const { t } = useTranslation();
  const { showAlert } = useAlert();
  const [open, setOpen] = useState(false);
  const { currentShifu, actions } = useShifu();

  const [autoSkipEmptyFields, setAutoSkipEmptyFields] = useState(false);

  const handleStartPreview = async () => {
    await actions.saveBlocks(currentShifu?.bid || '');
    // Handle the start preview action
    const result = await api.previewShifu({
      shifu_bid: currentShifu?.bid || '',
      skip: autoSkipEmptyFields,
      variables: {},
    });
    setOpen(false);
    showAlert({
      title: t('module.preview.title'),
      confirmText: t('module.preview.view'),
      cancelText: t('module.preview.close'),
      description: (
        <div className='flex flex-col space-y-2'>
          {t('module.preview.link')}：
          <a
            href={result}
            target='_blank'
            className='text-blue-500 hover:underline break-all'
          >
            {result}
          </a>
        </div>
      ),
      onConfirm: () => {
        window.open(result, '_blank');
      },
    });
  };
  return (
    <Dialog
      open={open}
      onOpenChange={setOpen}
    >
      <DialogTrigger asChild>
        <Button
          variant='ghost'
          size='sm'
          className='h-8 px-2 text-xs font-normal'
        >
          <PlayIcon /> {t('module.preview.preview')}
        </Button>
      </DialogTrigger>
      <DialogContent className='sm:max-w-md'>
        <DialogHeader>
          <DialogTitle className='text-center text-xl font-medium'>
            {t('module.preview.previewSettings')}
          </DialogTitle>
        </DialogHeader>

        <div>
          <div className='flex items-center justify-end space-x-2 mt-4'>
            <span className='text-sm'>{t('module.preview.autoSkip')}</span>
            <Switch
              checked={autoSkipEmptyFields}
              onCheckedChange={setAutoSkipEmptyFields}
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            className='w-full bg-primary hover:bg-primary-lighter'
            onClick={handleStartPreview}
          >
            {t('module.preview.startPreview')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default PreviewSettingsModal;
