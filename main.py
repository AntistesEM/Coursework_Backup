import requests
import json
from datetime import datetime
from tqdm.auto import tqdm
from pprint import pprint
import sys


class VK:
    url = 'https://api.vk.com/method/'

    def __init__(self, user, token_, count_):
        self.count = count_
        self.token = token_
        self.user = user
        self.params_default = {
            'access_token': self.token,
            'v': '5.131',
        }

    def get_list_albums(self):
        albums_dict = {}
        album_list = []
        url = self.url + 'photos.getAlbums'
        parameters = {
            'need_system': 1,
            'owner_id': self.user
        }
        response = requests.get(
            url,
            params={**parameters, **self.params_default}
        ).json()
        for album in response['response']['items']:
            albums_dict.setdefault(album['title'], {'id': album['id']})
            album_list.append(str(album['id']))
        return album_list, albums_dict

    def get_photos(self):
        album_list, albums_dict = self.get_list_albums()
        if input('Показать список доступных альбомов(да/нет)? ') in ['да',
                                                                     'yes']:
            pprint(albums_dict)
            print(album_list)
        self.album_id = input('Введите id альбома или оставьте поле пустым, '
                              'тогда будут загружены фотографии профиля: ')
        url = self.url + 'photos.get'
        if self.album_id == '':
            self.album_id = 'profile'
        elif self.album_id not in album_list:
            sys.exit('Ошибка: альбома с таким идентификатором нет!!!')
        if self.count == '':
            self.count = 5
        parameters = {
            'album_id': self.album_id,
            'owner_id': self.user,
            'count': self.count,
            'photo_sizes': 1,
            'extended': 1
        }
        response = requests.get(
            url,
            params={**parameters, **self.params_default}
        ).json()
        return response['response']['items']

    def find_max_size_photo(self):
        dict_photos_max = {}
        for photo in self.get_photos():
            for photo_size in reversed(photo['sizes']):
                list_type_photo = ['w', 'z', 'y', 'x', 'r', 'q', 'p',
                                   'o', 'm', 's']
                for type_ in list_type_photo:
                    if type_ == photo_size['type']:
                        dict_photos_max.setdefault(
                            photo['id'], {
                                'date': photo['date'],
                                'likes': photo['likes']['count'],
                                'size': photo_size['type'],
                                'url': photo_size['url']
                            }
                        )
                        break
        print(f'Количество найденных фотографий = {len(dict_photos_max)}')
        return dict_photos_max


class YandexDisk(VK):
    url = 'https://cloud-api.yandex.net/'

    def __init__(self, token_):
        super().__init__(user_vk.user, user_vk.token, user_vk.count)
        self.token = token_
        self.user_id = user_vk.user
        # self.album_id = user_vk.album_id
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'OAuth {token_}'
        }
        self.json_main = []
        self.photo_dict = user_vk.find_max_size_photo()

    def add_folder(self):
        url = self.url + 'v1/disk/resources'
        requests.put(url, headers=self.headers,
                     params={'path': f'id_{self.user_id}'})
        requests.put(
            url,
            headers=self.headers,
            params={'path': f'id_{self.user_id}/id_{user_vk.album_id}'}
        )
        return f'/id_{self.user_id}/id_{user_vk.album_id}/'

    def request(self, photo, date=''):
        url = self.url + 'v1/disk/resources/upload'
        parametrs = {
            'path': f"{self.add_folder()}"
                    f"{str(self.photo_dict[photo]['likes'])}{date}.jpg",
            'url': self.photo_dict[photo]['url']
        }
        response = requests.post(url, headers=self.headers, params=parametrs)
        self.json_main.append(
            {'file_name': f"{str(self.photo_dict[photo]['likes'])}"
                          f"{date}.jpg",
             'size': self.photo_dict[photo]['size']
             }
        )
        return f"{str(self.photo_dict[photo]['likes'])}{date}.jpg", response

    def copy_photo_to_yandex(self):
        likes = []
        for photo in tqdm(
                self.photo_dict,
                desc='Загрузка: ',
                file=sys.stdout,
                colour='green'
        ):
            if self.photo_dict[photo]['likes'] not in likes:
                likes.append(self.photo_dict[photo]['likes'])
                file_name, response = self.request(photo)
            else:
                timestamp = self.photo_dict[photo]['date']
                date = f"_{datetime.fromtimestamp(timestamp):%Y-%m-%d}"
                file_name, response = self.request(photo, date)
            if not response.ok:
                return f'Возникла ошибка {response.status_code}'
            else:
                with open('log.json', 'w') as file_:
                    json.dump(self.json_main, file_, indent=4)
                tqdm.write(
                    f'Статус: {response.status_code}. '
                    f'Загрузка файла {file_name} завершена. '
                    f'Данные записаны в файл {file_.name}.'
                )


if __name__ == '__main__':
    print('Для корректной работы необходимо в файл "token.txt" поместить '
          'access_token для VK и OAuth-токен для Yandex.')
    with open('token.txt') as file:
        token = file.readlines()
    user_vk = VK(
        input('Введите id пользователя: '),
        token[0],
        input('Введите количество загружаемых фото или оставьте поле пустым, '
              'тогда будут загружены 5 фотографий: ')
    )
    user_yandex = YandexDisk(token[1])
    user_yandex.copy_photo_to_yandex()
