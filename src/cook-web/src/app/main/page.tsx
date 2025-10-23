'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  PlusIcon,
  StarIcon as StarOutlineIcon,
  RectangleStackIcon as RectangleStackOutlineIcon,
} from '@heroicons/react/24/outline';
import {
  TrophyIcon,
  RectangleStackIcon,
  StarIcon,
} from '@heroicons/react/24/solid';
import api from '@/api';
import { Shifu } from '@/types/shifu';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { CreateShifuDialog } from '@/components/create-shifu-dialog';
import { useToast } from '@/hooks/useToast';
import { useRouter } from 'next/navigation';
import Loading from '@/components/loading';
import { useTranslation } from 'react-i18next';
import { ErrorWithCode } from '@/lib/request';
import ErrorDisplay from '@/components/ErrorDisplay';
import { useUserStore } from '@/store';
interface ShifuCardProps {
  id: string;
  image: string | undefined;
  title: string;
  description: string;
  isFavorite: boolean;
}

const ShifuCard = ({
  id,
  image,
  title,
  description,
  isFavorite,
}: ShifuCardProps) => {
  const router = useRouter();
  return (
    <Card
      className='w-full md:w-[calc(50%-1rem)] lg:w-[calc(33.33%-1rem)] cursor-pointer rounded-xl bg-background hover:scale-105 transition-all duration-200 ease-in-out'
      onClick={() => router.push(`/shifu/${id}`)}
    >
      <CardContent className='p-4 cursor-pointer'>
        <div className='flex flex-row items-center justify-between'>
          <div className='flex flex-row items-center mb-2 w-full'>
            <div className='p-2 h-10 w-10 rounded-lg bg-primary/10 mr-4 flex items-center justify-center shrink-0'>
              {image && (
                <img
                  src={image}
                  alt='recipe'
                  className='w-full h-full object-cover rounded-lg'
                />
              )}
              {!image && <TrophyIcon className='w-6 h-6 text-primary' />}
            </div>

            <h3 className='font-medium text-gray-900 leading-5 whitespace-nowrap overflow-hidden text-ellipsis'>
              {title}
            </h3>
          </div>
          {isFavorite && <StarIcon className='w-5 h-5 text-yellow-400' />}
        </div>
        <div>
          <p className='mt-1 text-sm text-gray-500 line-clamp-3 break-words break-all'>
            {description}
          </p>
        </div>
      </CardContent>
    </Card>
  );
};

const ScriptManagementPage = () => {
  const { toast } = useToast();
  const { t } = useTranslation();
  const isInitialized = useUserStore(state => state.isInitialized);
  const isGuest = useUserStore(state => state.isGuest);
  const [activeTab, setActiveTab] = useState('all');
  const [shifus, setShifus] = useState<Shifu[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [showCreateShifuModal, setShowCreateShifuModal] = useState(false);
  const [error, setError] = useState<{ message: string; code?: number } | null>(
    null,
  );
  const pageSize = 30;
  const currentPage = useRef(1);
  const containerRef = useRef(null);

  const fetchShifusRef = useRef<(() => Promise<void>) | null>(null);

  const fetchShifus = useCallback(async () => {
    if (loading || !hasMore) return;

    setLoading(true);
    try {
      const { items } = await api.getShifuList({
        page_index: currentPage.current,
        page_size: pageSize,
        is_favorite: activeTab === 'favorites',
      });
      if (items.length < pageSize) {
        setHasMore(false);
      }

      setShifus(prev => {
        // Prevent duplicate records
        const existingIds = new Set(prev.map(shifu => shifu.bid));
        const newItems = items.filter(
          (item: Shifu) => !existingIds.has(item.bid),
        );
        return [...prev, ...newItems];
      });
      currentPage.current += 1;
      setLoading(false);
    } catch (error: any) {
      console.error('Failed to fetch shifus:', error);
      setLoading(false);
      if (error instanceof ErrorWithCode) {
        // Pass the error code and original message to ErrorDisplay
        // ErrorDisplay will handle the translation based on error code
        setError({ message: error.message, code: error.code });
      } else {
        // For unknown errors, pass a generic error code
        setError({ message: error.message || 'Unknown error', code: 0 });
      }
    }
  }, [loading, hasMore, activeTab]);

  // Store the latest fetchShifus in ref
  fetchShifusRef.current = fetchShifus;
  const onCreateShifu = async (values: any) => {
    try {
      await api.createShifu(values);
      toast({
        title: t('common.core.createSuccess'),
        description: t('common.core.createSuccessDescription'),
      });
      setShifus([]);
      setHasMore(true);
      currentPage.current = 1;
      fetchShifus();
      setShowCreateShifuModal(false);
    } catch (error) {
      toast({
        title: t('common.core.createFailed'),
        description:
          error instanceof Error
            ? error.message
            : t('common.core.unknownError'),
        variant: 'destructive',
      });
    }
  };

  const handleCreateShifuModal = () => setShowCreateShifuModal(true);

  useEffect(() => {
    setShifus([]);
    setHasMore(true);
    currentPage.current = 1;
    setError(null);
  }, [activeTab]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !isInitialized) return;

    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && hasMore && fetchShifusRef.current) {
          fetchShifusRef.current();
        }
      },
      { threshold: 0.1 },
    );

    observer.observe(container);
    return () => observer.disconnect();
  }, [hasMore, isInitialized]);

  // Centralized login check - redirect if not logged in after initialization
  useEffect(() => {
    if (isInitialized && isGuest) {
      const currentPath = encodeURIComponent(
        window.location.pathname + window.location.search,
      );
      window.location.href = `/login?redirect=${currentPath}`;
      return;
    }
  }, [isInitialized, isGuest]);

  // Fetch data when user is initialized
  useEffect(() => {
    if (isInitialized && fetchShifusRef.current) {
      if (shifus.length === 0 && !loading) {
        fetchShifusRef.current();
      }
    }
  }, [isInitialized]);

  if (error) {
    return (
      <div className='h-full bg-gray-50 p-0'>
        <ErrorDisplay
          errorCode={error.code || 0}
          errorMessage={error.message}
          onRetry={() => {
            setError(null);
            setShifus([]);
            setHasMore(true);
            currentPage.current = 1;
            fetchShifus();
          }}
        />
      </div>
    );
  }

  return (
    <div className='h-full bg-gray-50 p-0'>
      <div className='max-w-7xl mx-auto h-full overflow-hidden flex flex-col'>
        <div className='flex justify-between items-center mb-5'>
          <h1 className='text-2xl font-semibold text-gray-900'>
            {t('common.core.shifu')}
          </h1>
        </div>
        <div className='flex space-x-3 mb-5'>
          <Button
            size='sm'
            variant='outline'
            onClick={handleCreateShifuModal}
          >
            <PlusIcon className='w-5 h-5 mr-1' />
            {t('common.core.createBlankShifu')}
          </Button>
          <CreateShifuDialog
            open={showCreateShifuModal}
            onOpenChange={setShowCreateShifuModal}
            onSubmit={onCreateShifu}
          />
        </div>
        <Tabs
          defaultValue='all'
          className='mb-0'
          onValueChange={setActiveTab}
        >
          <TabsList className='bg-stone-50 px-0'>
            <TabsTrigger value='all'>
              {activeTab == 'all' && (
                <RectangleStackIcon className='w-5 h-5 mr-1 text-primary' />
              )}
              {activeTab != 'all' && (
                <RectangleStackOutlineIcon className='w-5 h-5 mr-1' />
              )}
              {t('common.core.all')}
            </TabsTrigger>
            <TabsTrigger value='favorites'>
              {activeTab == 'favorites' && (
                <StarIcon className='w-5 h-5 mr-1 text-primary' />
              )}
              {activeTab != 'favorites' && (
                <StarOutlineIcon className='w-5 h-5 mr-1' />
              )}
              {t('common.core.favorites')}
            </TabsTrigger>
          </TabsList>
          <TabsContent
            value='all'
            className=' flex-1 overflow-auto'
          ></TabsContent>
          <TabsContent value='favorites'></TabsContent>
        </Tabs>
        <div className='flex-1 overflow-auto'>
          <div className='flex flex-wrap gap-4'>
            {shifus.map(shifu => (
              <ShifuCard
                id={shifu.bid + ''}
                key={shifu.bid}
                image={shifu.avatar}
                title={shifu.name || ''}
                description={shifu.description || ''}
                isFavorite={shifu.is_favorite || false}
              />
            ))}
          </div>
          <div
            ref={containerRef}
            className='w-full h-10 flex items-center justify-center'
          >
            {loading && <Loading />}
            {!hasMore && shifus.length > 0 && (
              <p className='text-gray-500 text-sm'>
                {t('common.core.noMoreShifus')}
              </p>
            )}
            {!loading && !hasMore && shifus.length == 0 && (
              <p className='text-gray-500 text-sm'>
                {t('common.core.noShifus')}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ScriptManagementPage;
