#pragma once
// Generated by chatty from exemples/exemple.chat
// DO NOT EDIT
#include <karm-math/vec.h>
namespace hideo {

struct ICompositor {
  static constexpr auto _UID = 0x9763fd6ae0868ca0;
  static constexpr auto _NAME = "Compositor";

  template <typename T> struct _Client;

  template <typename R> auto _dispatch(R &r);

  virtual ~ICompositor() = default;

  static constexpr auto createWindow_UID = 0x7110f2964d70557a;
  virtual Res<Window> createWindow(Vec2f const &size) = 0;
};

template <typename T> struct ICompositor::_Client : public ICompositor {
  T _t;

  _Client(T t) : _t{t} {}

  Res<Window> createWindow(Vec2f const &size) {
    return _t.template invoke<ICompositor, createWindow_UID,
                              Res<Window>(Vec2f const &)>(size);
  }
};

template <typename R> auto ICompositor::_dispatch(R &r) {
  switch (r.id()) {

  case createWindow_UID: {
    return r.reply(createWindow(r.template get<Vec2f const &>()));
  }

  default:
    return r.error();
  }
}

} // namespace hideo