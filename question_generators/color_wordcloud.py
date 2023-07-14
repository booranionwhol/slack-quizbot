# import matplotlib.pyplot as plt
import sys
from wordcloud import WordCloud
import random
from PIL import Image  # for loading image png as mask
import numpy as np

words = [
    'blue',
    'red',
    'green',
    'purple',
    'orange',
    'black',
    'grey',
    'brown',
    'pink',
    'yellow',
]
words = " ".join(words)

COLOURS = [
    'blue',
    'red',
    'green',
    'purple',
    'orange',
    'black',
    'grey',
    'brown',
    'pink',
]

colour_remap = {
    'orange': 'darkorange',
    'pink': 'hotpink',
    'blue': 'royalblue',
    'brown': 'sienna',
    'purple': 'blueviolet',
    'grey': 'lightgray',

}


class OutputImage():
    def __init__(self, max_words):
        self.max_words = max_words
        self.current_word_num = 1  # Increment for each word drawn

        print(f'Max words: {max_words}')
        self.winning_word_position = 0
        self.pick_random_word()
        print(f'Initial random word pos: {self.winning_word_position}')

        self.COLOURS = COLOURS
        random.shuffle(self.COLOURS)

        self.correct_word = ''  # Will be updated later
        # self.correct_word = random.choice(self.COLOURS)
        # self.CORRECT_WORD_SELECTED = False
        self.colours_not_correct = []

        # print(f'Correct word: {self.correct_word}')

    def build_incorrect_colour_list(self):
        self.colours_not_correct = list(COLOURS)
        self.colours_not_correct.remove(self.correct_word)

    def pick_random_word(self, new_min_pos=1):
        self.winning_word_position = random.randrange(
            new_min_pos, self.max_words)

    def random_colour_not_myself(self, word):
        # self.colours_not_correct already doesn't have winning colour
        # Remove the current colour also.
        colours_not_correct = [
            x for x in self.COLOURS if x != word]
        return random.choice(colours_not_correct)

    def remap_colour(self, colour):
        return colour_remap.get(colour, colour)

    def random_color_func(self, word=None, font_size=None, position=None, orientation=None, font_path=None, random_state=None):
        # h = int(360.0 * 45.0 / 255.0)
        # s = int(100.0 * 255.0 / 255.0)
        # l = int(100.0 * float(random_state.randint(60, 120)) / 255.0)

        # print(word, font_size)
        if self.current_word_num == self.winning_word_position:
            if font_size >= 60:
                self.pick_random_word(new_min_pos=self.current_word_num)
                print(
                    f'This was supposed to be the selected word, but its too big. Chosen another: {self.winning_word_position}')
            elif word not in self.COLOURS:
                self.pick_random_word(new_min_pos=self.current_word_num)
                print(
                    f'This word {word}, pos: {self.current_word_num} was selected, but we dont want to draw this colour. Chosen new: {self.winning_word_position}')
            else:
                print(
                    f'Winning word selected!: word: {word}, pos: {self.current_word_num}, size: {font_size}')
                self.correct_word = word
                # output_colour = word
        else:
            pass
            # output_colour = self.random_colour_not_correct(word)
            # print(f'{self.CORRECT_WORD_SELECTED} - {word} {font_size} {output_colour}')

        self.current_word_num += 1  # Increment for the next word drawn
        # return self.remap_colour(output_colour)
        return word
        # return "hsl({}, {}%, {}%)".format(h, s, l)

    def recolourise(self, word=None, font_size=None, position=None, orientation=None, font_path=None, random_state=None):
        if self.current_word_num == self.winning_word_position:
            output_colour = word
        else:
            output_colour = self.random_colour_not_myself(word)

        self.current_word_num += 1
        return self.remap_colour(output_colour)

    def create_image(self, image_mask=None, output_filename=None):
        # x, y = np.ogrid[:300, :300]
        # mask = (x - 150) ** 2 + (y - 150) ** 2 > 130 ** 2
        # mask = 255 * mask.astype(int)

        # file_content = open("question_generators/words.txt").read()
        # d = path.dirname(__file__) if "__file__" in locals() else os.getcwd()

        if image_mask:
            print(f'Image mask used. Mask: {image_mask}')
            mask_png = np.array(Image.open(image_mask))
        else:
            mask_png = None

        wordcloud = WordCloud(font_path=r'/mnt/c/Windows/Fonts/Verdana.ttf',
                              background_color='white',
                              repeat=True,
                              min_font_size=12,
                              width=random.randint(800,1000),
                              height=600,
                              max_words=self.max_words,
                              max_font_size=150,
                              mask=mask_png,
                              contour_color='#3D4976',
                              contour_width=1,
                              color_func=self.random_color_func,
                              ).generate(words)

        self.current_word_num = 1  # reset counter, so recolourise() can count up again
        self.build_incorrect_colour_list()
        image = wordcloud.recolor(color_func=self.recolourise)
        if output_filename:
            filename = f'{output_filename}_{self.correct_word}.png'
            print(f'Saving image to file {filename}')
            image = wordcloud.to_file(filename)
        else:
            image = wordcloud.to_image()
        self.image = image


if __name__ == '__main__':
    image = OutputImage(max_words=random.randint(80, 130))
    if len(sys.argv) == 2:
        image.create_image(output_filename=sys.argv[1])
    elif len(sys.argv) == 3:
        image.create_image(
            image_mask=sys.argv[2], output_filename=sys.argv[1])
    else:
        image.create_image()
        image.image.show()
    print(f'Correct answer: {image.correct_word}')
