'use client';

import type React from 'react';

import { useState, useRef, useEffect } from 'react';
import { Upload } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';
import { uploadFile } from '@/lib/file';
import { useToast } from '@/hooks/useToast';
import { useTranslation } from 'react-i18next';
import api from '@/api';
type ImageResource = {
  resourceUrl?: string;
  resourceTitle?: string;
  resourceScale?: number;
};
type ImageUploaderProps = {
  value?: ImageResource;
  onChange?: (resource: ImageResource) => void;
};
// FIXME: from config
const agiImgUrlRegexp =
  /^https?:\/\/(?:resource\.ai-shifu\.cn)\/[a-f0-9]{32}(?:\/?|\.[a-z]{3,4})?$/i;

const ImageUploader: React.FC<ImageUploaderProps> = ({ value, onChange }) => {
  const { t } = useTranslation();
  const [resourceUrl, setResourceUrl] = useState<string>('');
  const [inputUrl, setInputUrl] = useState<string>(value?.resourceUrl || '');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [resourceTitle, setResourceTitle] = useState<string>(
    value?.resourceTitle || '',
  );
  const [resourceScale, setResourceScale] = useState<number>(
    value?.resourceScale || 100,
  );
  const [uploadProgress, setUploadProgress] = useState(0);
  const resourceInputRef = useRef<HTMLInputElement>(null);

  const { toast } = useToast();

  const resetState = () => {
    setResourceUrl('');
    setInputUrl('');
    setResourceTitle('');
    setResourceScale(100);
    if (resourceInputRef.current) {
      resourceInputRef.current.value = '';
    }
  };

  // Handle post-upload logic inside the uploadImage function
  const uploadImage = async (file: File) => {
    setIsUploading(true);
    try {
      const response = await uploadFile(
        file,
        '/api/shifu/upfile',
        undefined,
        undefined,
        progress => {
          setUploadProgress(progress);
        },
      );

      if (!response.ok) {
        throw new Error(
          `${t('component.fileUploader.uploadFailed')}: ${response.statusText}`,
        );
      }

      const res = await response.json();
      if (res.code !== 0) {
        throw new Error(res.message);
      }

      if (!response.ok) {
        throw new Error(t('component.fileUploader.uploadFailed'));
      }
      setResourceUrl(res.data);
      setResourceTitle(file.name);
      setResourceScale(100);
      const img = new Image();
      img.src = res.data;
    } catch (error) {
      console.error('Error uploading image:', error);
      alert(t('component.fileUploader.uploadImageFailed'));
    } finally {
      setIsUploading(false);
    }
  };

  const handleUrlUpload = async () => {
    if (!inputUrl) return;
    try {
      new URL(inputUrl);
    } catch (error) {
      console.error('Error uploading image:', error);
      toast({
        title: t('component.fileUploader.checkImageUrl'),
        variant: 'destructive',
      });
      return;
    }
    if (agiImgUrlRegexp.test(inputUrl)) {
      setResourceUrl(inputUrl);
    } else {
      setIsUploading(true);
      try {
        const url = await api.upfileByUrl({ url: inputUrl }).catch(err => {
          console.error('Error uploading image:', err);
          toast({
            title: t('component.fileUploader.checkImageUrl'),
            variant: 'destructive',
          });
        });
        setResourceUrl(url);
        setResourceTitle('');
        setResourceScale(100);
      } catch (error) {
        console.error('Error uploading image:', error);
        toast({
          title: t('component.fileUploader.checkImageUrl'),
          variant: 'destructive',
        });
      } finally {
        setIsUploading(false);
      }
      return;
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      uploadImage(file);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const resource = e.dataTransfer.files?.[0];
    if (resource) {
      uploadImage(resource);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  useEffect(() => {
    onChange?.({
      resourceUrl,
      resourceTitle,
      resourceScale,
    });
  }, [resourceUrl, resourceTitle, resourceScale]);

  useEffect(() => {
    handleUrlUpload();
  }, []);

  return (
    <div className='space-y-6'>
      {!resourceUrl ? (
        <>
          <div className='text-xs'>
            <h2 className='font-bold mb-4'>
              {t('component.fileUploader.url')}
            </h2>
            <div className='flex gap-2'>
              <Input
                placeholder={t('component.fileUploader.pasteOrInputImageUrl')}
                value={inputUrl}
                onChange={e => setInputUrl(e.target.value)}
                className='flex-1'
              />
              <Button
                onClick={handleUrlUpload}
                disabled={isUploading || !inputUrl}
                className='w-24 h-8'
              >
                {t('component.fileUploader.run')}
              </Button>
            </div>
          </div>

          <div>
            <h2 className='font-bold mb-4'>
              {t('component.fileUploader.upload')}
            </h2>
            <Card
              className='border-dashed border-2 text-center flex flex-col items-center justify-center min-h-[200px] p-2'
              onDrop={handleDrop}
              onDragOver={handleDragOver}
            >
              {isUploading ? (
                <div className='mt-2'>
                  <div className='w-full bg-gray-200 rounded-full h-2.5'>
                    <div
                      className='bg-primary h-2.5 rounded-full'
                      style={{ width: `${uploadProgress}%` }}
                    ></div>
                  </div>
                  <p className='text-xs text-gray-500 mt-1 text-center'>
                    {t('component.fileUploader.uploading')} {uploadProgress}%
                  </p>
                </div>
              ) : (
                <>
                  <input
                    type='file'
                    ref={resourceInputRef}
                    onChange={handleFileChange}
                    className='hidden'
                    accept='image/*'
                  />
                  <Upload className='h-10 w-10 text-gray-400 mb-4' />
                  <div className='mb-2'>
                    {t('component.fileUploader.dragOrClickToUpload')}
                    <button
                      className='text-blue-600 hover:underline'
                      onClick={() => resourceInputRef.current?.click()}
                    >
                      {t('component.fileUploader.clickToUpload')}
                    </button>
                  </div>
                  <p className='text-gray-500'>
                    {t('component.fileUploader.tips')}
                  </p>
                </>
              )}
            </Card>
          </div>
        </>
      ) : (
        <div className='flex flex-col items-center'>
          <img
            src={resourceUrl || '/placeholder.svg'}
            alt='Uploaded image'
            className='max-w-full max-h-[400px] object-contain mb-4'
          />
          <div className='flex items-center w-full mb-2'>{resourceUrl}</div>
          <div className='flex items-center w-full mb-2'>
            <div className='text-sm w-20'>
              {t('component.fileUploader.imageTitle')}
            </div>
            <Input
              className='flex-1'
              value={resourceTitle}
              onChange={e => setResourceTitle(e.target.value.slice(0, 100))}
              placeholder={t('component.fileUploader.imageTitlePlaceholder')}
              maxLength={100}
            />
          </div>

          <div className='flex items-center w-full mb-2'>
            <div className='text-sm w-20'>
              {t('component.fileUploader.imageScale')}
            </div>
            <div className='flex items-center gap-1'>
              <Input
                type='number'
                min={1}
                max={100}
                step={10}
                value={resourceScale}
                onChange={e => {
                  const value = Number(e.target.value);
                  if (!isNaN(value) && value >= 1 && value <= 100) {
                    setResourceScale(value);
                  }
                }}
                placeholder='100'
              />
              <span className='text-gray-500'>%</span>
            </div>
          </div>

          <Button
            variant='outline'
            className='w-full py-2'
            onClick={resetState}
          >
            {t('component.fileUploader.replaceImage')}
          </Button>
        </div>
      )}
    </div>
  );
};
export default ImageUploader;
