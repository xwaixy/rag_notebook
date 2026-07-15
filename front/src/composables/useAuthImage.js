import { apiConfig } from '../config/api';
import { getAuthHeaders, getAuthToken } from '../utils/auth';

export function useAuthImage() {
  const getAllImages = async (md5) => {
    if (!getAuthToken()) return {};

    try {
      const response = await fetch(apiConfig.endpoints.knowledgeImagesAll(md5), {
        headers: getAuthHeaders(),
      });
      if (!response.ok) return {};
      const result = await response.json();
      if (result.code !== 200 || !result.data?.images) return {};
      return result.data.images;
    } catch {
      return {};
    }
  };

  const resolveImageUrls = (imagePaths, imageMap) => {
    return imagePaths
      .map(p => {
        const basename = p.split('/').pop().replace(/\.[^.]+$/, '');
        const key = Object.keys(imageMap).find(
          k => k.replace(/\.[^.]+$/, '') === basename
        );
        return key ? imageMap[key] : null;
      })
      .filter(Boolean);
  };

  return { getAllImages, resolveImageUrls };
}
