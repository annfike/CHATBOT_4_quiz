import os
import random
import re

import redis
import vk_api
import vk_api as vk
from dotenv import load_dotenv
from thefuzz import fuzz
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkEventType, VkLongPoll
from vk_api.utils import get_random_id

from main import get_question, make_questions_and_answers


def get_keyboard():
    keyboard = VkKeyboard(one_time=True)

    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.SECONDARY)
    keyboard.add_button('Сдаться', color=VkKeyboardColor.SECONDARY)

    keyboard.add_line()  # Переход на вторую строку
    keyboard.add_button('Мой счет', color=VkKeyboardColor.SECONDARY)
    return keyboard


def handle_new_question_request(event, vk_api, r, questions_and_answers):
    user = event.user_id
    question_and_answer = get_question(questions_and_answers)
    question = question_and_answer[0]
    r.set(user, question)
    keyboard = get_keyboard()
    vk_api.messages.send(
        user_id=user,
        keyboard=keyboard.get_keyboard(),
        message=question,
        random_id=random.randint(1,1000)
    )


def handle_solution_attempt(event, vk_api, r, questions_and_answers):
    user = event.user_id
    if r.get(user):
        user_answer = event.text
        question = r.get(user)
        right_answer = questions_and_answers[question]
        right_answer = re.split('[.(]',right_answer)[0]
        match = fuzz.WRatio(user_answer, right_answer) 
        keyboard = get_keyboard()
        if match > 70:
            vk_api.messages.send(
                user_id=user,
                random_id=get_random_id(),
                keyboard=keyboard.get_keyboard(),
                message='Правильно! Поздравляю! Для следующего вопроса нажми "Новый вопрос"'
            )
        else:
            vk_api.messages.send(
                user_id=user,
                random_id=get_random_id(),
                keyboard=keyboard.get_keyboard(),
                message='Неправильно… Попробуешь ещё раз?'
            )
    else:
        vk_api.messages.send(
            user_id=user,
            random_id=get_random_id(),
            keyboard=keyboard.get_keyboard(),
            message='Привет! Я бот для викторин.'
        )
        

def handle_give_up(event, vk_api, r, questions_and_answers):
    user = event.user_id
    question = r.get(user)
    right_answer = questions_and_answers[question]
    vk_api.messages.send(
            user_id=user,
            random_id=get_random_id(),
            message=f'Правильный ответ: {right_answer}'
        )
    handle_new_question_request(event, vk_api, r, questions_and_answers)


def main() -> None:

    load_dotenv()
    vk_token = os.getenv('VK_TOKEN')
    redis_host = os.getenv('REDIS_HOST')
    redis_port = os.getenv('REDIS_PORT')
    redis_password = os.getenv('REDIS_PASSWORD')

    r = redis.StrictRedis(
        host=redis_host,
        port=redis_port,
        password=redis_password,
        charset='utf-8',
        decode_responses=True
        )
    questions_and_answers = make_questions_and_answers('quiz-questions')

    vk_session = vk.VkApi(token=vk_token)
    vk_api = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            if event.text == 'Новый вопрос':
                handle_new_question_request(event, vk_api, r, questions_and_answers)
            if event.text == 'Сдаться':
                handle_give_up(event, vk_api, r, questions_and_answers)
            else:
                handle_solution_attempt(event, vk_api, r, questions_and_answers)


if __name__ == '__main__':
    main()   

    
