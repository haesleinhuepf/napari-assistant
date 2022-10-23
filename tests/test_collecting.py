def test_collecting():
    from napari_tools_menu import register_function

    @register_function(menu="Filtering / noise removal > Fantasy (clesperanto)")
    def fantasy_filter(image:"napari.types.ImageData") -> "napari.types.ImageData":
        return image

    @register_function(menu="Filtering / noise removal > Difference of Fantasy (clesperanto)")
    def difference_of_fantasy_filter(image:"napari.types.ImageData") -> "napari.types.ImageData":
        return image

    from napari_assistant._categories import find_function

    func = find_function("Fantasy (clesperanto)")

    assert func is fantasy_filter
